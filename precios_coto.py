from botasaurus.browser import browser, Driver
from botasaurus.soupify import soupify
from botasaurus.user_agent import UserAgent
import pandas as pd
import time
from requests.exceptions import HTTPError
from datetime import datetime
from tqdm import tqdm
import random
import re
import os
import sys

@browser(create_error_logs=True, headless=False, block_images=False, parallel=1,
            user_agent=UserAgent.RANDOM,
)
def scrape_sub_subcategories(driver: Driver, suc: str) -> list:
    """Main function to scrape product data from a list of sub-subcategories."""
    categories_df = load_categories("categories/sub_sub_categorias.xlsx")
    products = []
    print(suc)
    # Utilizar tqdm para ver el progreso
    for _, row in tqdm(categories_df.iterrows(), total=len(categories_df), desc="Scraping categories"):
        base_url, category_data = prepare_category(row, suc)
        base_url = base_url.replace("cotodigital3", "cotodigital").replace("browse", "categoria")
        products += paginate_products(driver, base_url, category_data, suc)

    return products


def load_categories(file_path: str) -> pd.DataFrame:
    """Loads sub-subcategories from an Excel file."""
    return pd.read_excel(file_path)


def prepare_category(row, suc) -> tuple:
    """Prepare the base URL and category data for a given row."""
    base_url = f"{row['url']}?Nrpp=10000&idSucursal={suc}&No="
    category_data = {
        "category": row["categoria"],
        "subcategory": row["subcategoria"],
        "sub_subcategory": row["sub_subcategoria"]
    }
    return base_url, category_data

class SuppressOutput:
    def __enter__(self):
        # Redirigir stdout y stderr a /dev/null (en Windows, es nul)
        self._original_stdout = sys.stdout
        self._original_stderr = sys.stderr
        sys.stdout = open(os.devnull, 'w')
        sys.stderr = open(os.devnull, 'w')
        
    def __exit__(self, exc_type, exc_value, traceback):
        # Restaurar stdout y stderr
        sys.stdout.close()
        sys.stderr.close()
        sys.stdout = self._original_stdout
        sys.stderr = self._original_stderr


def paginate_products(driver: Driver, base_url: str, category_data: dict, suc:str) -> list:
    """Paginates through the product listings for a given category and scrapes data."""
    step, offset, products = 1000, 0, []
    while True:
        current_url = base_url + str(offset)
        soup = request_page(driver, current_url)

        product_elements = soup.select('.producto-card')
        if not product_elements:
            break

        products += extract_product_data(product_elements,
                                        current_url, category_data, suc)

        if not more_products_available(soup):
            break

        offset += step

    return products

def request_page(driver: Driver, url: str):
    """Handles HTTP requests with retry logic for a given URL."""
    attempts, max_attempts = 0, 2
    block_wait_time = 1800  # Tiempo inicial de espera en segundos (30 minutos)
    random_sleep_min, random_sleep_max = 80, 90  # Límites iniciales para el random sleep en segundos

    while attempts < max_attempts:
        try:
            driver.get(url)
            # page_text = driver.select("*", wait=1.5)
            # Ajuste del tiempo de espera aleatorio
            with SuppressOutput(): # para evitar que printee en la consola
                driver.sleep(random.uniform(random_sleep_min, random_sleep_max))
            driver.click_at_point(100, 200)
            driver.scroll(by=random.uniform(1500, 2500), wait=5)
            driver.scroll_to_bottom(smooth_scroll=True, wait=3)
            soup = soupify(driver.page_html)

            if "Web Page Blocked" in soup.text:
                print(f"Blocked, waiting {block_wait_time // 60} minutes... {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}")
                time.sleep(block_wait_time)
                block_wait_time += 900  # Incrementar 15 minutos (900 segundos)
                random_sleep_min += 15  # Incrementar el mínimo de random sleep
                random_sleep_max += 15  # Incrementar el máximo de random sleep
                attempts += 1
                continue

            return soup

        except Exception as e:
            print(f"Error loading page {url}: {e}")
            attempts += 1
            time.sleep(300)  # Wait 5 minutes before retrying

    print(f"Max attempts reached for URL: {url}")
    return None


def extract_product_data(product_elements, current_url: str, category_data: dict, suc: str) -> list:
    """Extracts and returns product information from a list of HTML elements."""
    products = []
    scrape_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for product in product_elements:
        # Extraer datos del producto
        product_info = {
            'store_id': suc,
            'product_id': None,  # No hay un id único en el HTML
            'original_url': current_url,
            'product_url': get_product_url(product, suc),  # Usamos la URL de la imagen como referencia
            'description': get_text_from_element(product, 'h5', 'nombre-producto'),
            'unit_price': get_unit_price(product),
            'store_price': get_text_from_element(product, 'small', 'card-text'),
            'new_price': get_text_from_element(product, 'h4', 'card-title'),
            'scrap_time': scrape_time,
            **category_data
        }
        products.append(product_info)

    return products


def get_product_url(product, suc:str) -> str:
    """Constructs the product URL from the image URL."""
    image_element = product.select_one('img.product-image')
    if image_element:
        # Extraer el identificador del producto desde la URL de la imagen
        image_url = image_element.get('src')
        match = re.search(r'/(\d{8})\.', image_url)  # Buscar un patrón numérico de 8 dígitos
        if match:
            product_id = match.group(1)
            # Construir la URL del producto
            return f"https://www.cotodigital.com.ar/sitios/cdigi/productos/{product_id}/_/R-{product_id}-{product_id}-{suc}"
    return None



def get_unit_price(product) -> str:
    """Extracts the unit price from the product element."""
    unit_price_element = product.find('small', string=lambda text: "Precio por" in text if text else False)
    if unit_price_element:
        return unit_price_element.text.strip()
    return None


def get_text_from_element(product, tag: str, class_name: str) -> str:
    """Extracts and returns text content from an HTML element."""
    element = product.select_one(f"{tag}.{class_name}")
    if element:
        return element.text.strip()
    return None

def more_products_available(soup) -> bool:
    """Checks if more products are available based on the results count."""
    results_text = soup.find('strong', class_='d-block py-2')
    if results_text:
        match = re.search(r'\d+', results_text.text)  # Extraer solo los números
        if match:
            results_count = int(match.group())
            return results_count > 1000
    return False

def extract_measure_price(text):
    if pd.isna(text):
        return pd.Series([None, None])
    # Usar expresión regular para extraer medida y precio
    match = re.search(r'(?i)por (.+?)\s*:\s*\$([\d.,]+)', text)
    if match:
        unit_measure = match.group(1).strip()  # Extrae la medida
        unit_final_price = match.group(2).replace('.', '').replace(',', '.')  # Extrae el precio y convierte el formato
        return pd.Series([unit_measure, float(unit_final_price)])
    return pd.Series([None, None])

def clean_unit_price(value):
    if isinstance(value, str):
        return re.sub(r'\s+', ' ', value).strip()
    return value  # Dejar el valor sin cambios si no es una cadena

def clean_df(prices_df:pd.DataFrame):
    
    prices_df["unit_price"] = prices_df["unit_price"].apply(clean_unit_price)
    # Aplicar la función a la columna 'unit_price' para crear nuevas columnas
    prices_df[['unit_measure', 'unit_final_price']] = prices_df['unit_price'].apply(extract_measure_price)
    unit_mapping = {
    '1 Kilo': '1 Kilogramo',
    '1 Kilogramo escurrido': '1 Kilogramo',
    '1 Kilo escurrido': '1 Kilogramo',
    '100 Gramos': '100 Gramos',
    '100 Gramos escurridos': '100 Gramos',
    '1 Litro': '1 Litro',
    '1 Litro escurrido': '1 Litro',
    '1 Unidad escurrido': '1 Unidad'
    }

    # Reemplazar las unidades utilizando el diccionario de mapeo
    prices_df['unit_measure'] = prices_df['unit_measure'].replace(unit_mapping)
    
    prices_df["store_price"] = prices_df["store_price"].str.replace("$","").str.replace(".","").str.replace(",",".")
    prices_df['store_price'] = pd.to_numeric(prices_df['store_price'], errors='coerce')
    prices_df["new_price"] = prices_df["new_price"].str.replace("$","").str.replace(".","").str.replace(",",".")
    prices_df['new_price'] = pd.to_numeric(prices_df['new_price'], errors='coerce')
    
    return prices_df

def main():
    """Main function to load data, scrape, and save results."""
    # categories = load_categories("categories/sub_sub_categorias.xlsx")
    inicio = time.time()

    prices_dfs = []
    for suc in [
                200,
                # 91,  # 220, 44, 45, 203, 60,
                # 182,  # 197, 192, 188, 92,
                # 64,  # 235, 189, 75, 65, 107,
                # 215,  # 129, 131, 219,
                # 204,  # 178,
                # 165,  # 96,
                # 109,
                # 185,
                # 209
                ]:
        product_data = pd.DataFrame(
            scrape_sub_subcategories(data=str(suc)))
        prices_dfs.append(product_data)

    prices_df = pd.concat(prices_dfs, ignore_index=True)

    scrape_time = datetime.now().strftime("%Y_%m_%d")

    prices_df.to_pickle(f"output/productos_coto_{scrape_time}.pkl")
    
    prices_df = clean_df(prices_df)
    
    prices_df.to_parquet(f"clean_prices/productos_coto_{scrape_time}.parquet")

    final = time.time()

    tiempo_total = final - inicio
    horas, resto = divmod(tiempo_total, 3600)
    minutos, segundos = divmod(resto, 60)  
      
    with open("tiempo_ejecucion.txt", "w") as file:
        file.write(f"Tiempo total de ejecución: {int(horas)}:{int(minutos)}:{int(segundos)}\n")


if __name__ == "__main__":
    main()
    
