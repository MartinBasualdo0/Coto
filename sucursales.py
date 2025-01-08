import requests
from random_header_generator import HeaderGenerator
from bs4 import BeautifulSoup
import pandas as pd


def get_soup_from_url(url: str) -> BeautifulSoup:
    """Fetch the HTML content from the URL and return a BeautifulSoup object."""
    headers = HeaderGenerator()()
    response = requests.get(url, headers=headers)
    response.raise_for_status()  # Ensure we catch HTTP errors
    return BeautifulSoup(response.text, 'html.parser')


def extract_table_data(table) -> pd.DataFrame:
    """Extract data from a single HTML table and return it as a pandas DataFrame."""
    rows = table.find_all('tr')
    headers = [th.text.strip() for th in rows[0].find_all('th')]  # Get headers
    data = [[col.text.strip() for col in row.find_all('td')]
            for row in rows[1:]]  # Extract row data
    return pd.DataFrame(data, columns=headers)


def extract_all_tables(soup: BeautifulSoup) -> pd.DataFrame:
    """Find all tables in the BeautifulSoup object and concatenate them into a single DataFrame."""
    tables = soup.find_all('table')
    dataframes = [extract_table_data(table)
                  for table in tables]  # Process each table
    return pd.concat(dataframes, ignore_index=True)  # Combine all tables


def save_to_excel(df: pd.DataFrame, file_path: str) -> None:
    """Save the DataFrame to an Excel file."""
    df.to_excel(file_path, index=False)


def main():
    url = "https://www.coto.com.ar/mapassucursales/Sucursales/ListadoSucursales.aspx"
    soup = get_soup_from_url(url)
    df_final = extract_all_tables(soup)
    save_to_excel(df_final, "sucursales/sucursales.xlsx")


if __name__ == "__main__":
    main()
