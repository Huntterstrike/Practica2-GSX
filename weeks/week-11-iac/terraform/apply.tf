resource "terraform_data" "namespace" {
  triggers_replace = [sha256(local.namespace_manifest)]

  input = {
    file_name    = "week11-${var.environment_name}-namespace.yaml"
    manifest_b64 = base64encode(local.namespace_manifest)
  }

  provisioner "local-exec" {
    interpreter = ["PowerShell", "-Command"]
    command     = <<-EOT
      $manifest = [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String("${self.input.manifest_b64}"))
      $tempFile = Join-Path $env:TEMP "${self.input.file_name}"
      Set-Content -Path $tempFile -Value $manifest -Encoding utf8
      kubectl apply -f $tempFile
    EOT
  }

  provisioner "local-exec" {
    when        = destroy
    interpreter = ["PowerShell", "-Command"]
    command     = <<-EOT
      $manifest = [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String("${self.input.manifest_b64}"))
      $tempFile = Join-Path $env:TEMP "${self.input.file_name}"
      Set-Content -Path $tempFile -Value $manifest -Encoding utf8
      kubectl delete --ignore-not-found=true -f $tempFile
      if ($LASTEXITCODE -ne 0) { exit 0 }
    EOT
  }
}

resource "terraform_data" "app_pv" {
  triggers_replace = [sha256(local.app_pv_manifest)]

  input = {
    file_name    = "week11-${var.environment_name}-app-pv.yaml"
    manifest_b64 = base64encode(local.app_pv_manifest)
  }

  depends_on = [terraform_data.namespace]

  provisioner "local-exec" {
    interpreter = ["PowerShell", "-Command"]
    command     = <<-EOT
      $manifest = [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String("${self.input.manifest_b64}"))
      $tempFile = Join-Path $env:TEMP "${self.input.file_name}"
      Set-Content -Path $tempFile -Value $manifest -Encoding utf8
      kubectl apply -f $tempFile
    EOT
  }

  provisioner "local-exec" {
    when        = destroy
    interpreter = ["PowerShell", "-Command"]
    command     = <<-EOT
      $manifest = [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String("${self.input.manifest_b64}"))
      $tempFile = Join-Path $env:TEMP "${self.input.file_name}"
      Set-Content -Path $tempFile -Value $manifest -Encoding utf8
      kubectl delete --ignore-not-found=true -f $tempFile
      if ($LASTEXITCODE -ne 0) { exit 0 }
    EOT
  }
}

resource "terraform_data" "app_pvc" {
  triggers_replace = [sha256(local.app_pvc_manifest)]

  input = {
    file_name    = "week11-${var.environment_name}-app-pvc.yaml"
    manifest_b64 = base64encode(local.app_pvc_manifest)
  }

  depends_on = [
    terraform_data.namespace,
    terraform_data.app_pv,
  ]

  provisioner "local-exec" {
    interpreter = ["PowerShell", "-Command"]
    command     = <<-EOT
      $manifest = [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String("${self.input.manifest_b64}"))
      $tempFile = Join-Path $env:TEMP "${self.input.file_name}"
      Set-Content -Path $tempFile -Value $manifest -Encoding utf8
      kubectl apply -f $tempFile
    EOT
  }

  provisioner "local-exec" {
    when        = destroy
    interpreter = ["PowerShell", "-Command"]
    command     = <<-EOT
      $manifest = [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String("${self.input.manifest_b64}"))
      $tempFile = Join-Path $env:TEMP "${self.input.file_name}"
      Set-Content -Path $tempFile -Value $manifest -Encoding utf8
      kubectl delete --ignore-not-found=true -f $tempFile
      if ($LASTEXITCODE -ne 0) { exit 0 }
    EOT
  }
}

resource "terraform_data" "redis_stack" {
  triggers_replace = [sha256(local.redis_manifest_bundle)]

  input = {
    file_name    = "week11-${var.environment_name}-redis.yaml"
    manifest_b64 = base64encode(local.redis_manifest_bundle)
  }

  depends_on = [terraform_data.namespace]

  provisioner "local-exec" {
    interpreter = ["PowerShell", "-Command"]
    command     = <<-EOT
      $manifest = [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String("${self.input.manifest_b64}"))
      $tempFile = Join-Path $env:TEMP "${self.input.file_name}"
      Set-Content -Path $tempFile -Value $manifest -Encoding utf8
      kubectl apply -f $tempFile
    EOT
  }

  provisioner "local-exec" {
    when        = destroy
    interpreter = ["PowerShell", "-Command"]
    command     = <<-EOT
      $manifest = [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String("${self.input.manifest_b64}"))
      $tempFile = Join-Path $env:TEMP "${self.input.file_name}"
      Set-Content -Path $tempFile -Value $manifest -Encoding utf8
      kubectl delete --ignore-not-found=true -f $tempFile
      if ($LASTEXITCODE -ne 0) { exit 0 }
    EOT
  }
}

resource "terraform_data" "simple_app_stack" {
  triggers_replace = [sha256(local.simple_app_manifest_bundle)]

  input = {
    file_name    = "week11-${var.environment_name}-simple-app.yaml"
    manifest_b64 = base64encode(local.simple_app_manifest_bundle)
  }

  depends_on = [
    terraform_data.namespace,
    terraform_data.app_pvc,
    terraform_data.redis_stack,
  ]

  provisioner "local-exec" {
    interpreter = ["PowerShell", "-Command"]
    command     = <<-EOT
      $manifest = [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String("${self.input.manifest_b64}"))
      $tempFile = Join-Path $env:TEMP "${self.input.file_name}"
      Set-Content -Path $tempFile -Value $manifest -Encoding utf8
      kubectl apply -f $tempFile
    EOT
  }

  provisioner "local-exec" {
    when        = destroy
    interpreter = ["PowerShell", "-Command"]
    command     = <<-EOT
      $manifest = [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String("${self.input.manifest_b64}"))
      $tempFile = Join-Path $env:TEMP "${self.input.file_name}"
      Set-Content -Path $tempFile -Value $manifest -Encoding utf8
      kubectl delete --ignore-not-found=true -f $tempFile
      if ($LASTEXITCODE -ne 0) { exit 0 }
    EOT
  }
}

resource "terraform_data" "nginx_stack" {
  triggers_replace = [sha256(local.nginx_manifest_bundle)]

  input = {
    file_name    = "week11-${var.environment_name}-nginx.yaml"
    manifest_b64 = base64encode(local.nginx_manifest_bundle)
  }

  depends_on = [
    terraform_data.namespace,
    terraform_data.simple_app_stack,
  ]

  provisioner "local-exec" {
    interpreter = ["PowerShell", "-Command"]
    command     = <<-EOT
      $manifest = [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String("${self.input.manifest_b64}"))
      $tempFile = Join-Path $env:TEMP "${self.input.file_name}"
      Set-Content -Path $tempFile -Value $manifest -Encoding utf8
      kubectl apply -f $tempFile
    EOT
  }

  provisioner "local-exec" {
    when        = destroy
    interpreter = ["PowerShell", "-Command"]
    command     = <<-EOT
      $manifest = [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String("${self.input.manifest_b64}"))
      $tempFile = Join-Path $env:TEMP "${self.input.file_name}"
      Set-Content -Path $tempFile -Value $manifest -Encoding utf8
      kubectl delete --ignore-not-found=true -f $tempFile
      if ($LASTEXITCODE -ne 0) { exit 0 }
    EOT
  }
}
