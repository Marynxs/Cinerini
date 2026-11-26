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

output "instance_id" {
  value = aws_instance.api.id
}

output "public_ip" {
  value = aws_eip.api.public_ip
}

# Endereço da API, que vai para o Caddy e para o VITE_API_URL da Vercel.
output "api_domain" {
  value = "${replace(aws_eip.api.public_ip, ".", "-")}.sslip.io"
}

output "db_endpoint" {
  value = aws_db_instance.main.address
}

output "ssh_command" {
  value = "ssh -i ~/.ssh/cinerini-aws ec2-user@${aws_eip.api.public_ip}"
}
