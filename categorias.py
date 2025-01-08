import pandas as pd
# from botasaurus import AntiDetectRequests
from bs4 import BeautifulSoup
import requests
from botasaurus.browser import browser, Driver
from botasaurus.soupify import soupify

# URLs y solicitud inicial
BASE_URL = "https://www.cotodigital3.com.ar"
LINK = f"{BASE_URL}/sitios/cdigi/"


@browser(create_error_logs=True, headless=False, block_images_and_css=True)
def fetch_page_content(driver: Driver, url):
    """
    Realiza una solicitud GET a la URL dada utilizando botasaurus con anti-detección.
    """
    driver.get(url)
    html = driver.select("*", wait=1.5)
    soup = soupify(html)
    with open("coto_content_categories.html", 'w', encoding='utf-8') as f:
        f.write(str(soup.prettify()))  # Guarda el contenido HTML con formato
    return extract_serializable_data(soup)


def extract_serializable_data(soup):
    """
    Extrae los datos serializables del objeto BeautifulSoup.
    En este caso, se extraen las categorías, subcategorías, etc.
    """
    categorias_data, subcategorias_data, sub_sub_categorias_data = extraer_datos(
        soup)
    return {
        "categorias": categorias_data,
        "subcategorias": subcategorias_data,
        "sub_sub_categorias": sub_sub_categorias_data
    }


def obtener_categorias(soup):
    categorias_data = []
    categorias_html = soup.select('li.atg_store_dropDownParent')

    for categoria in categorias_html:
        categoria_id = categoria.get('id')
        nombre_categoria = categoria.find('a').text.strip()

        categorias_data.append({
            'id': categoria_id,
            'nombre': nombre_categoria
        })

    return categorias_data


def obtener_subcategorias(categoria_html, nombre_categoria):
    subcategorias_data = []
    # subcategorias_html = categoria_html.select('ul.sub_category > li > h2 > a')

    for subcat in categoria_html.select('ul.sub_category li h2 a'):
        subcategoria_nombre = subcat.get_text(strip=True)
        subcategoria_url = subcat['href']
        subcategorias_data.append({
            'categoria': nombre_categoria,  # asociamos con la categoría principal
            'subcategoria': subcategoria_nombre,
            'url': BASE_URL + subcategoria_url
        })
    # print(subcategorias_data)
    return subcategorias_data


def obtener_sub_subcategorias(categoria_html, nombre_categoria):
    sub_sub_categorias_data = []
    for subsubcat_block in categoria_html.select('div[id^="thrd_level_"]'):
        # Encontramos la subcategoría padre de este bloque de sub-subcategorías
        subcategoria_padre = subsubcat_block.find_previous(
            'h2').get_text(strip=True)

        for subsubcat in subsubcat_block.select('li a'):
            sub_sub_categorias_data.append({
                'categoria': nombre_categoria,  # asociamos con la categoría principal
                # asociamos con la subcategoría correspondiente
                # esta bien esto?
                'subcategoria': subcategoria_padre.replace("(+)", ""),
                'sub_subcategoria': subsubcat.get_text(strip=True),
                'url': BASE_URL + subsubcat['href']
            })
    # print(sub_sub_categorias_data)

    return sub_sub_categorias_data


def extraer_datos(soup):
    categorias_data = []
    subcategorias_data = []
    sub_sub_categorias_data = []

    # Extraer las categorías principales
    categorias_html = soup.select('li.atg_store_dropDownParent')

    for categoria_html in categorias_html:
        categoria_id = categoria_html.get('id')
        nombre_categoria = categoria_html.find('a').text.strip()

        categorias_data.append({
            'id': categoria_id,
            'nombre': nombre_categoria
        })

        # Obtener las subcategorías de la categoría actual
        sub_categorias = obtener_subcategorias(  # esto devuelve una lista de dict
            categoria_html, nombre_categoria)
        subcategorias_data.extend(sub_categorias)

        sub_sub_categorias = obtener_sub_subcategorias(  # esto devuelve una lista de dict
            categoria_html, nombre_categoria)
        sub_sub_categorias_data.extend(sub_sub_categorias)

    return categorias_data, subcategorias_data, sub_sub_categorias_data


def limpiar_columnas(df, columna):
    return (df[columna].str.replace(r'\t.*', '', regex=True)
            .str.replace(r'\n', ' ', regex=True)
            .str.strip())


def guardar_datos(df_categorias, df_subcategorias, df_sub_sub_categorias):
    df_categorias.to_excel('categories/categorias.xlsx', index=False)
    df_subcategorias.to_excel('categories/subcategorias.xlsx', index=False)
    df_sub_sub_categorias.to_excel(
        'categories/sub_sub_categorias.xlsx', index=False)


def main_categorias():
    page_data = fetch_page_content(LINK)

    # Extraemos los datos del diccionario retornado
    categorias_data = page_data['categorias']
    subcategorias_data = page_data['subcategorias']
    sub_sub_categorias_data = page_data['sub_sub_categorias']

    df_categorias = pd.DataFrame(categorias_data)
    df_subcategorias = pd.DataFrame(subcategorias_data)
    df_sub_sub_categorias = pd.DataFrame(sub_sub_categorias_data)
    print(df_sub_sub_categorias)
    df_subcategorias['nombre'] = limpiar_columnas(
        df_subcategorias, 'subcategoria')
    df_sub_sub_categorias['subcategoria'] = limpiar_columnas(
        df_sub_sub_categorias, 'subcategoria')

    guardar_datos(df_categorias, df_subcategorias, df_sub_sub_categorias)


if __name__ == "__main__":
    main_categorias()
