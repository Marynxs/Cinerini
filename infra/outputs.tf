# Valores que o workflow de deploy e as próximas etapas precisam conhecer.
# Nenhum é segredo: um ARN de role não concede nada sem o token do GitHub.

output "ecr_repository_url" {
  value = aws_ecr_repository.api.repository_url
}

output "github_deploy_role_arn" {
  value = aws_iam_role.github_deploy.arn
}

output "ec2_instance_profile" {
  value = aws_iam_instance_profile.ec2.name
}
