# Source Tree

The project will use a Turborepo monorepo structure, separating deployable apps (api, web) from shared packages (shared-types, ui). Note: For the MVP, the asynchronous worker logic will reside within the apps/api project to accelerate development, with a plan to refactor it into a dedicated apps/worker application post-MVP for independent scaling.
