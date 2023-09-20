# Leggi il contenuto del file
$content = Get-Content -Path "agids.txt"

# Estrai i numeri dalle linee e invoca il comando python per ciascuno
foreach ($line in $content) {
    if ($line -match "\[(\d+)\]") {
        Invoke-Expression -Command "python .\main.py --multiple"
    }
}