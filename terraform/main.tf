terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

locals {
  service_name = "cargodb"
  image        = "${var.region}-docker.pkg.dev/${var.project_id}/shipsafe/${local.service_name}:latest"
}

resource "google_artifact_registry_repository" "shipsafe" {
  location      = var.region
  repository_id = "shipsafe"
  format        = "DOCKER"
  description   = "ShipSafe Docker images"
}

resource "google_cloud_run_v2_service" "cargodb" {
  name     = local.service_name
  location = var.region

  depends_on = [google_artifact_registry_repository.shipsafe]

  template {
    containers {
      image = local.image

      env {
        name  = "GCP_PROJECT"
        value = var.project_id
      }
      env {
        name  = "GCP_REGION"
        value = var.region
      }
      env {
        name  = "GEMINI_MODEL"
        value = var.gemini_model
      }

      # Secrets from Secret Manager — nothing hardcoded (rule 5)
      env {
        name = "MONGODB_ATLAS_URI"
        value_source {
          secret_key_ref {
            secret  = "MONGODB_ATLAS_URI"
            version = "latest"
          }
        }
      }
      env {
        name = "VOYAGE_API_KEY"
        value_source {
          secret_key_ref {
            secret  = "VOYAGE_API_KEY"
            version = "latest"
          }
        }
      }
      env {
        name = "MDB_MCP_API_CLIENT_ID"
        value_source {
          secret_key_ref {
            secret  = "MDB_MCP_API_CLIENT_ID"
            version = "latest"
          }
        }
      }
      env {
        name = "MDB_MCP_API_CLIENT_SECRET"
        value_source {
          secret_key_ref {
            secret  = "MDB_MCP_API_CLIENT_SECRET"
            version = "latest"
          }
        }
      }
      env {
        name = "ATLAS_PROJECT_ID"
        value_source {
          secret_key_ref {
            secret  = "ATLAS_PROJECT_ID"
            version = "latest"
          }
        }
      }

      resources {
        limits = {
          cpu    = "2"
          memory = "2Gi"
        }
      }

      ports {
        container_port = 8080
      }
    }

    service_account = google_service_account.cargodb_sa.email

    scaling {
      min_instance_count = 0
      max_instance_count = 10
    }
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }
}

resource "google_service_account" "cargodb_sa" {
  account_id   = "cargodb-sa"
  display_name = "CargoDB Cloud Run Service Account"
}

resource "google_project_iam_member" "secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.cargodb_sa.email}"
}

resource "google_project_iam_member" "vertex_user" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.cargodb_sa.email}"
}

resource "google_artifact_registry_repository_iam_member" "sa_pusher" {
  project    = var.project_id
  location   = var.region
  repository = google_artifact_registry_repository.shipsafe.name
  role       = "roles/artifactregistry.writer"
  member     = "serviceAccount:${google_service_account.cargodb_sa.email}"
}

resource "google_cloud_run_v2_service_iam_member" "public_invoker" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.cargodb.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

output "service_url" {
  value = google_cloud_run_v2_service.cargodb.uri
}

output "image" {
  value = local.image
}
