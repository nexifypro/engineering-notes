terraform {
  required_version = ">= 1.10"
  required_providers {
    aws  = { source = "hashicorp/aws", version = "~> 6.0" }
    http = { source = "hashicorp/http", version = "~> 3.4" }
  }
}

provider "aws" {
  region = "us-east-1"
}

module "baseline" {
  source      = "../../modules/baseline"
  name_prefix = "example-prod"
  tags        = { Environment = "prod" }
}

output "audit_bucket" {
  value = module.baseline.audit_bucket
}
