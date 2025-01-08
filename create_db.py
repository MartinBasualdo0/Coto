import pandas as pd
from glob import glob

# SACAR LAS SUCURSALES QUE NO SEAN 200
# Leer y concatenar todos los archivos de "clean_prices" (son archivos .parquet)
files = glob('./clean_prices/*.parquet')
df_list = [pd.read_parquet(file) for file in files]
df = pd.concat(df_list, ignore_index=True)

# Exportar el DataFrame a un archivo .parquet
df.to_parquet('coto_prices.parquet')