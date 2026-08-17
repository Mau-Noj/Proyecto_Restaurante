output "app_public_ip" {
  value = module.compute.public_ip
}

output "db_endpoint" {
  value = module.database.db_endpoint
}

output "db_secret_arn" {
  value = module.database.db_secret_arn
}

output "redis_endpoint" {
  value = module.cache.redis_endpoint
}

output "media_bucket" {
  value = module.storage.bucket_name
}
