## Get JWT token from Supabase
# This PowerShell script logs in to Supabase using your email/password and prints the JWT access token.
# It reads SUPABASE_URL and SUPABASE_ANON_KEY from the .env file in the project root.
# Edit the `$email` and `$password` variables (or set them as environment variables) before running.

# Load environment variables from .env (simple parsing, ignores comments)
$envPath = "d:/WorkSpace/mindcradle/backend/.env"
Get-Content $envPath | ForEach-Object {
    if ($_ -match "^\s*([^#=]+)=([^#]+)$") {
        $key = $matches[1].Trim()
        $value = $matches[2].Trim()
        Set-Item -Path "Env:$key" -Value $value
    }
}

# Set your credentials (replace with your own values or export them as env vars before running)
$email = "imshubham7004@gmail.com"
$password = "Shubham@220"

# Build request payload
$payload = @{ email = $email; password = $password } | ConvertTo-Json

# Prepare headers – Supabase expects the anon key as apikey
$headers = @{
    apikey = $Env:SUPABASE_ANON_KEY
    "Content-Type" = "application/json"
}

# Perform login request
$response = Invoke-RestMethod -Uri ("$Env:SUPABASE_URL/auth/v1/token?grant_type=password") -Method POST -Headers $headers -Body $payload

# Output the JWT token
Write-Host "Your JWT access token:`n$response.access_token"
