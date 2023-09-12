# Leggi il contenuto del file
$content = Get-Content -Path "agids.txt"

# Estrai i numeri dalle linee e invoca il comando python per ciascuno
foreach ($line in $content) {
    if ($line -match "\[(\d+)\]") {
        $number = $matches[1]
        Invoke-Expression -Command "python .\main.py --execute --confirm --agid=$number"
    }
}