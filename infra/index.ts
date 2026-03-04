/**
 * TechNova Support Bot — Pulumi Infrastructure
 *
 * Resources created:
 *   - ECR repository
 *   - Docker image (built from ../Dockerfile.lambda, pushed to ECR)
 *   - IAM role for Lambda
 *   - CloudWatch Log Group
 *   - Lambda function (container image, 512 MB, 30 s timeout)
 *   - API Gateway HTTP API with all routes
 *   - Lambda invoke permission for API Gateway
 *
 * Stack config (set via `pulumi config set`):
 *   apiKey          — NEAM_API_KEY for the bot (default: dev-key-change-me)
 *   anthropicApiKey — ANTHROPIC_API_KEY for Claude LLM (optional)
 */

import * as pulumi from "@pulumi/pulumi";
import * as aws from "@pulumi/aws";
import * as docker from "@pulumi/docker";

const cfg = new pulumi.Config();

// ── AWS account info ──────────────────────────────────────────────────────────

const caller = aws.getCallerIdentity({});
const region = aws.getRegion({});

// ── ECR Repository ────────────────────────────────────────────────────────────

const repo = new aws.ecr.Repository("technova-support-bot", {
  name: "technova-support-bot",
  forceDelete: true,
  imageTagMutability: "MUTABLE",
  imageScanningConfiguration: { scanOnPush: false },
  tags: { Project: "technova-support-bot" },
});

// ECR lifecycle policy — keep only the 5 most recent images
new aws.ecr.LifecyclePolicy("technova-ecr-lifecycle", {
  repository: repo.name,
  policy: JSON.stringify({
    rules: [
      {
        rulePriority: 1,
        description: "Keep last 5 images",
        selection: { tagStatus: "any", countType: "imageCountMoreThan", countNumber: 5 },
        action: { type: "expire" },
      },
    ],
  }),
});

// ECR auth token — used by the Docker provider to push the image
const ecrToken = aws.ecr.getAuthorizationTokenOutput({
  registryId: caller.then((c) => c.accountId),
});

// ── Docker image — build & push ───────────────────────────────────────────────
// @pulumi/docker v4 builds with `docker buildx` supporting cross-platform
// (linux/amd64 required for Lambda even on Apple Silicon Macs).

const image = new docker.Image("technova-lambda-image", {
  build: {
    context: "..",           // repo root — so COPY data/ and COPY app/ resolve
    dockerfile: "../Dockerfile.lambda",
    platform: "linux/amd64",
  },
  imageName: pulumi.interpolate`${repo.repositoryUrl}:latest`,
  registry: {
    server: repo.repositoryUrl,
    username: ecrToken.apply((t) => t.userName),
    password: ecrToken.apply((t) => t.password),
  },
});

// ── IAM Role for Lambda ───────────────────────────────────────────────────────

const lambdaRole = new aws.iam.Role("technova-lambda-role", {
  name: "technova-lambda-role",
  assumeRolePolicy: JSON.stringify({
    Version: "2012-10-17",
    Statement: [
      {
        Effect: "Allow",
        Principal: { Service: "lambda.amazonaws.com" },
        Action: "sts:AssumeRole",
      },
    ],
  }),
  tags: { Project: "technova-support-bot" },
});

new aws.iam.RolePolicyAttachment("technova-lambda-basic-exec", {
  role: lambdaRole.name,
  policyArn: aws.iam.ManagedPolicy.AWSLambdaBasicExecutionRole,
});

// ── CloudWatch Log Group ──────────────────────────────────────────────────────

const logGroup = new aws.cloudwatch.LogGroup("technova-lambda-logs", {
  name: "/aws/lambda/technova-support-bot",
  retentionInDays: 7,
  tags: { Project: "technova-support-bot" },
});

// ── Lambda Function ───────────────────────────────────────────────────────────

const apiKey = cfg.get("apiKey") ?? "dev-key-change-me";
const anthropicKey = cfg.get("anthropicApiKey") ?? "";

const lambdaFn = new aws.lambda.Function(
  "technova-support-bot",
  {
    name: "technova-support-bot",
    packageType: "Image",
    imageUri: image.repoDigest,   // digest-pinned URI for reproducibility
    role: lambdaRole.arn,
    timeout: 30,
    memorySize: 512,
    environment: {
      variables: {
        NEAM_API_KEY: apiKey,
        ANTHROPIC_API_KEY: anthropicKey,
        SESSION_DIR: "/tmp/sessions",
      },
    },
    tags: { Project: "technova-support-bot" },
  },
  { dependsOn: [logGroup] }
);

// ── API Gateway HTTP API ──────────────────────────────────────────────────────

const api = new aws.apigatewayv2.Api("technova-api", {
  name: "technova-support-bot-api",
  protocolType: "HTTP",
  corsConfiguration: {
    allowOrigins: ["*"],
    allowMethods: ["GET", "POST", "OPTIONS"],
    allowHeaders: ["Content-Type", "Authorization"],
    maxAge: 3600,
  },
  tags: { Project: "technova-support-bot" },
});

// Lambda proxy integration (payload format 2.0)
const integration = new aws.apigatewayv2.Integration("technova-lambda-integration", {
  apiId: api.id,
  integrationType: "AWS_PROXY",
  integrationUri: lambdaFn.invokeArn,
  payloadFormatVersion: "2.0",
});

// Routes — mirrors the original Neam agent HTTP channel
const routeKeys = [
  "GET /health",
  "GET /api/v1/claw",
  "POST /api/v1/claw/support_bot/sessions/{key}/message",
  "POST /api/v1/claw/support_bot/sessions/{key}/reset",
  "GET /api/v1/metrics",
];

routeKeys.forEach((routeKey) => {
  const id = routeKey.replace(/[^a-zA-Z0-9]/g, "-").toLowerCase();
  new aws.apigatewayv2.Route(`route-${id}`, {
    apiId: api.id,
    routeKey,
    target: pulumi.interpolate`integrations/${integration.id}`,
  });
});

// Default stage with auto-deploy
const stage = new aws.apigatewayv2.Stage("technova-stage", {
  apiId: api.id,
  name: "$default",
  autoDeploy: true,
  tags: { Project: "technova-support-bot" },
});

// Allow API Gateway to invoke the Lambda
new aws.lambda.Permission("technova-api-gateway-permission", {
  action: "lambda:InvokeFunction",
  function: lambdaFn.name,
  principal: "apigateway.amazonaws.com",
  sourceArn: pulumi.interpolate`${api.executionArn}/*/*`,
});

// ── Outputs ───────────────────────────────────────────────────────────────────

// invokeUrl already has a trailing slash — don't add another
export const apiUrl        = stage.invokeUrl.apply(u => u.replace(/\/$/, ""));
export const healthUrl     = pulumi.interpolate`${stage.invokeUrl}health`;
export const chatUrl       = pulumi.interpolate`${stage.invokeUrl}api/v1/claw/support_bot/sessions/{key}/message`;
export const lambdaArn     = lambdaFn.arn;
export const ecrRepository = repo.repositoryUrl;
export const awsRegion     = region.then((r) => r.name);
export const awsAccount    = caller.then((c) => c.accountId);
