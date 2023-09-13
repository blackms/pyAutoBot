#!/bin/bash

# Estrai i numeri tra parentesi quadre dal file agids.txt
numbers=$(grep -o '\[\([0-9]*\)\]' agids.txt | awk -F'[][]' '{print $2}')

# Per ogni numero, esegui il comando desiderato
for num in $numbers; do
    echo "main.py --execute --confirm --agid=$num"
    # Decommenta la riga seguente se vuoi eseguire effettivamente il comando
    python3 main.py --execute --confirm --agid=$num
done