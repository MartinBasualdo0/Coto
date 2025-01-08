Para correr:

- Tener instalado Python y NodeJS.

El archivo "categorias.py" busca las categorías y subcategorías disponibles. No es necesario correrlo siempre. El resultado están en los excels dentro de la carpeta de "categories".

No recomiendo correr "sucursales.py" que busca todas las sucursales disponibles porque los precios, según entiendo por Ley, son los mismos en todas las sucursales.

precios_coto.py es el más relevante. Puede llegar a tardar más o menos 1 hora. El resultado se guarda en la carpeta "clean_prices" con formato .parquet. El último lo corrí el 29 de octubre.

"create_db.py" crea la dataframe concatenada con todos los precios, es decir, la serie histórica. Debería crear un archivo llamado "coto_prices.parquet" en la carpeta principal.
