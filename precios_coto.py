from botasaurus.browser import browser, Driver
from botasaurus.soupify import soupify
import pandas as pd
import time
from requests.exceptions import HTTPError
from datetime import datetime
from tqdm import tqdm
import random
import re

@browser(create_error_logs=True, headless=False, block_images=False)
def scrape_sub_subcategories(driver: Driver, suc: str) -> list:
    """Main function to scrape product data from a list of sub-subcategories."""
    categories_df = load_categories("categories/sub_sub_categorias.xlsx")
    products = []
    print(suc)
    # Utilizar tqdm para ver el progreso
    for _, row in tqdm(categories_df.iterrows(), total=len(categories_df), desc="Scraping categories"):
        base_url, category_data = prepare_category(row, suc)
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


def paginate_products(driver: Driver, base_url: str, category_data: dict, suc:str) -> list:
    """Paginates through the product listings for a given category and scrapes data."""
    step, offset, products = 1000, 0, []
    while True:
        current_url = base_url + str(offset)
        soup = request_page(driver, current_url)

        if soup is None:
            print(f"Skipping category {
                  category_data['sub_subcategory']} due to errors.")
            break

        product_elements = soup.select('li[id^="li_prod"]')
        if not product_elements:
            # print(f"No more products (offset={offset}) for category {
            #       category_data['sub_subcategory']}. Ending scraping.")
            break

        products += extract_product_data(product_elements,
                                         current_url, category_data, suc)

        if not more_products_available(soup):
            break

        offset += step

    return products

# Make HTTP requests and handle errors


def request_page(driver: Driver, url: str):
    """Handles HTTP requests with retry logic for a given URL."""
    attempts, max_attempts = 0, 2
    while attempts < max_attempts:
        try:
            driver.get(url)
            page_text = driver.select("*", wait=1.5)
            driver.scroll(by=random.uniform(900, 1200))
            # driver.sleep(random.uniform(1, 5))
            soup = soupify(page_text)

            if "Web Page Blocked" in soup.text:
                print("Blocked, waiting 30 minutes...")
                time.sleep(1800)  # Wait 30 minutes
                attempts += 1
                continue
            
            # driver.humane_click('span.atg_store_newPrice')
            # driver.humane_click('span.atg_store_newPrice')

            return soup

        except Exception as e:
            print(f"Error loading page {url}: {e}")
            attempts += 1
            time.sleep(300)  # Wait 5 minutes before retrying

    print(f"Max attempts reached for URL: {url}")
    return None

# Extract product data from the page


def extract_product_data(product_elements, current_url: str, category_data: dict, suc:str) -> list:
    """Extracts and returns product information from a list of HTML elements."""
    products = []
    scrape_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for product in product_elements:
        # Obtener el precio usando la primera clase
        store_price = get_text_from_element(product, 'span', 'atg_store_productPrice')
        
        if not store_price:
            store_price = get_text_from_element(product, 'span', 'price_regular_precio')

        # Crear el diccionario con la información del producto
        product_info = {
            'store_id': suc,
            'product_id': product.get('id'),
            'original_url': current_url,
            'product_url': get_product_url(product),
            'description': get_text_from_element(product, 'div', 'descrip_full'),
            'unit_price': get_text_from_element(product, 'span', 'unit'),
            'store_price': store_price, 
            'new_price': get_text_from_element(product, 'span', 'atg_store_newPrice'),
            "scrap_time": scrape_time,
            **category_data
        }

        # Añadir el producto a la lista de productos
        products.append(product_info)

    return products

# Helper to check if there are more products to paginate


def more_products_available(soup) -> bool:
    """Checks if more products are available based on the results count."""
    results_count = int(soup.find('span', id='resultsCount').text)
    return results_count > 1000

# Get product URL


def get_product_url(product) -> str:
    """Extracts the product URL from the HTML element."""
    product_link = product.find('a', href=True)
    if product_link:
        return f"https://www.cotodigital3.com.ar{product_link['href']}"
    return None

# Get text from an element by tag and class


def get_text_from_element(product, tag: str, class_name: str) -> str:
    """Extracts and returns text content from an HTML element."""
    element = product.find(tag, class_=class_name)
    if element:
        return element.text.strip()
    return None

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

def clean_df(prices_df:pd.DataFrame):
    
    prices_df["unit_price"] = prices_df["unit_price"].apply(lambda x: re.sub(r'\s+', ' ', x).strip())
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
    
