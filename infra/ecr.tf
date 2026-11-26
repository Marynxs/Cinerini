resource "aws_ecr_repository" "api" {
  name = "${var.project}-api"

  # Tag imutável: a imagem marcada com um commit é sempre a daquele commit.
  # Sem isso, um push poderia sobrescrever a tag de uma versão anterior, e o
  # rollback para ela traria outra coisa.
  image_tag_mutability = "IMMUTABLE"

  # Varredura básica de vulnerabilidades, sem custo, a cada push.
  image_scanning_configuration {
    scan_on_push = true
  }

  # Permite o destroy com imagens dentro. O que se perde é regenerável a
  # partir de qualquer commit, e um repositório que bloqueia o destroy é
  # exatamente a sobra que continua cobrando.
  force_delete = true
}

# Guardar todas as versões cobra armazenamento para sempre; cinco cobrem
# qualquer rollback realista.
resource "aws_ecr_lifecycle_policy" "api" {
  repository = aws_ecr_repository.api.name

  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Mantém as cinco imagens mais recentes"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 5
      }
      action = { type = "expire" }
    }]
  })
}
