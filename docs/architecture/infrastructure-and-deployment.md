# Infrastructure and Deployment

- **Infrastructure as Code**: AWS CDK will be used to define and provision all AWS resources.
- **CI/CD**: GitHub Actions will orchestrate a backend-first deployment. The backend CDK stack is deployed to AWS, and only upon its successful completion is the Vercel frontend deployment triggered. This prevents frontend/backend version mismatches.
