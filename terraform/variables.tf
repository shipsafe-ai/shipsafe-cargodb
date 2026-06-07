variable "project_id" {
  description = "GCP project ID"
  type        = string
  default     = "shipsafe-ai"
}

variable "region" {
  description = "GCP region for Cloud Run"
  type        = string
  default     = "us-central1"
}

variable "gemini_model" {
  description = "Gemini model identifier (from config, not hardcoded in logic)"
  type        = string
  default     = "gemini-2.5-flash"
}
