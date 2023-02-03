import numpy as np
import pandas as pd
from bs4 import BeautifulSoup
import time

from selenium import webdriver
from selenium.webdriver.common.by import By

import yaml
# https://herrmann.tech/en/blog/2021/02/05/how-to-deal-with-international-data-formats-in-python.html
import locale

class AmazonOrderScraper:
    def __init__(self, _config_param):
        self.username = _config_param['username']
        self.password = _config_param['password']
        self.amazon = _config_param['amazon_domain']
        if self.amazon == 'amazon.it':
            locale.setlocale(locale.LC_ALL, settings_locale)
            self.page_not_found_message = 'Impossibile trovare la pagina'
        else: #not default: to be implemented
            locale.setlocale(locale.LC_ALL, settings_locale)
            self.page_not_found_message = 'Impossibile trovare la pagina'

        self.date = np.array([])
        self.cost = np.array([])
        self.order_id = np.array([])
        self.addressee = np.array([])
        #self.order_details = []

    def URL(self, year: int, start_index: int) -> str:
        return "https://www." + self.amazon + "/gp/your-account/order-history" + \
               "?orderFilter=year-" + \
               str(year) + \
               "&ref_=ppx_yo2ov_dt_b_filter_all_y" + \
               str(year) + \
               "&search=&startIndex=" + \
               str(start_index)


    def scrape_order_data(self, start_year: int, end_year: int) -> pd.DataFrame:
        years = list(range(start_year, end_year + 1))
        driver = self.start_driver_and_manually_login_to_amazon()

        for year in years:
            driver.get(
                self.URL(year, 0)
            )

            number_of_pages = self.find_max_number_of_pages(driver)

            self.scrape_first_page_before_progressing(driver)

            for i in range(number_of_pages):
                self.scrape_page(driver, year, i)

            print(f"Order data extracted for {year}")

        order_details_ = self.scrape_order_details(driver)

        driver.close()

        print("Scraping done :)")

        order_data = pd.DataFrame({
            "Date": self.date,
            "Cost €": self.cost,
            "Order ID": self.order_id,
            "Addressee": self.addressee,
        })
        order_details = pd.DataFrame(order_details_, columns=['order_id', 'Product ID', 'Name', 'Link',
                                                                  'Categories', 'Purchased Price €', 'Current Price €',
                                                                    'Refound €'])
        order_data_full = order_data.merge(order_details, left_on='Order ID', right_on='order_id')
        order_data_full.drop(columns=['order_id'], inplace=True)
        # order_data = self.prepare_dataset(order_data)

        # order_data.to_csv(r"amazon-orders.csv")

        return order_data_full

    def scrape_item_details(self, driver: webdriver, URL):
        time.sleep(2)

        driver.get('http://' + URL)
        page_source = driver.page_source
        #page_content = BeautifulSoup(page_source, "html.parser")
        page_content = BeautifulSoup(page_source, "lxml")

        categories=[]
        if page_content.head.title is not None and page_content.head.title.string == self.page_not_found_message:
            title, price_current = None, None
        else:
            for cat_levels in page_content.findAll("a", attrs={'class': 'a-link-normal a-color-tertiary'}):
                categories.append(cat_levels.string.strip())
            if page_content.find("span", attrs={'id': 'productTitle'}) is not None:
                title = page_content.find("span", attrs={'id': 'productTitle'}).string.strip()
                print('title =' + title)
            else:
                title = None
            if page_content.find("span", attrs={'class': 'a-price aok-align-center reinventPricePriceToPayMargin priceToPay'}) is not None:
                price_current = page_content.find("span", attrs={'class': 'a-price aok-align-center reinventPricePriceToPayMargin priceToPay'}).find("span", attrs={'class': 'a-offscreen'}).string.strip()
            elif page_content.find("ul", attrs={'class': 'a-unordered-list a-nostyle a-button-list a-horizontal'}) is not None:
                if page_content.find("ul", attrs={'class': 'a-unordered-list a-nostyle a-button-list a-horizontal'}).find("span", attrs={'class' : 'a-size-base a-color-price a-color-price'}) is not None:
                    price_current = page_content.find("ul", attrs={'class': 'a-unordered-list a-nostyle a-button-list a-horizontal'}).find("span", attrs={'class' : 'a-size-base a-color-price a-color-price'}).string.strip()
                else:
                    price_current = None
            else:
                price_current = None
        return categories, title, price_current

    def scrape_order_details(self, driver: webdriver):
        time.sleep(2)
        order_details = []
        ord_details_url = 'https://www.' + self.amazon + '/gp/your-account/order-details/ref=ppx_yo_dt_b_order_details_o01?ie=UTF8&orderID='

        for or_id in self.order_id:
            driver.get(ord_details_url + or_id)
            page_source = driver.page_source
            page_content = BeautifulSoup(page_source, "html.parser")
            if len(page_content.findAll("div", {"class": "a-box-group od-shipments"})) > 0:
                item_info = page_content.findAll("div", {"class": "a-box-group od-shipments"})[0]
            elif len(page_content.findAll("div", {"class": "a-box shipment"})) > 0:
                item_info = page_content.findAll("div", {"class": "a-box shipment"})[0]
            else:
                item_info = None

            items = []
            #orders.append(i.text.strip())
            #for i in range(0, len(item_info.findAll("a",{"class": "a-link-normal"}))):
            #   if i%2 == 1:
            if item_info is not None and item_info.findAll("span", {"class": "a-size-small a-color-price"}) is not None:
                for i in range(0, len(item_info.findAll("span", {"class": "a-size-small a-color-price"}))):
                    link = self.amazon + item_info.findAll("div",{"class": "a-fixed-left-grid-col yohtmlc-item a-col-right"})[i].findAll("a",{"class": "a-link-normal"})[0].get("href").rsplit('/', 1)[0]
                    #   name = item_info.findAll("a",{"class": "a-link-normal"})[i].text.strip()
                    #   price = item_info.findAll("span",{"class": "a-size-small a-color-price"})[i//2].text.strip()
                    price_purchased = item_info.findAll("span", {"class": "a-size-small a-color-price"})[i].text.strip()
                    product_id = link.split("/")[-1]
                    if item_info.find("div", {"class": "actions"}) is not None:
                        if len(item_info.find("div", {"class": "actions"}).findAll("span", {"class": "a-color-success a-text-bold"})) > 0:
                            refound = item_info.find("div", {"class": "actions"}).findAll("span", {"class": "a-color-success a-text-bold"})[2].text.strip()
                        else:
                            refound = None
                    else:
                        refound = None
                    print('product_id = ' + product_id)
                    categories, title, price_current = self.scrape_item_details(driver, link)
                    items.append((or_id, product_id, title, link, categories, price_purchased, price_current, refound))
            else:
                categories, title, price_current, product_id, link, price_current, price_purchased, refound = [], None, None, None, None, None, None, None
                items.append((or_id, product_id, title, link, categories, price_purchased, price_current, refound))
            order_details.extend(items)
        return order_details

    def start_driver_and_manually_login_to_amazon(self) -> webdriver:
        options = webdriver.ChromeOptions()
        options.add_argument("--start-maximized")
        driver = webdriver.Chrome(r'chromedriver_win32\chromedriver.exe', options=options)

        amazon_sign_in_url = "https://www." + self.amazon + "/ap/signin?openid.pape.max_auth_age=0&openid.return_to=https%3A%2F%2Fwww.amazon.it%2F%3Fref_%3Dnav_custrec_signin&openid.identity=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0%2Fidentifier_select&openid.assoc_handle=itflex&openid.mode=checkid_setup&openid.claimed_id=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0%2Fidentifier_select&openid.ns=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0&"

        driver.get(amazon_sign_in_url)

        time.sleep(2)



        #https://dzone.com/articles/automate-sign-in-selenium-web-driver
        #https://bobbyhadz.com/blog/python-attributeerror-webdriver-object-has-no-attribute-find-element-by-id
        username_textbox = driver.find_element(By.ID, "ap_email")
        username_textbox.send_keys(self.username)
        Continue_button = driver.find_element(By.ID, "continue")
        Continue_button.submit()
        time.sleep(2)
        password_textbox = driver.find_element(By.ID, "ap_password")
        password_textbox.send_keys(self.password)
        SignIn_button = driver.find_element(By.ID, "auth-signin-button-announce")
        SignIn_button.submit()

        time.sleep(2)  # allows time for manual sign in - increase if you need more time

        return driver

    def find_max_number_of_pages(self, driver: webdriver) -> int:
        time.sleep(2)
        page_source = driver.page_source
        page_content = BeautifulSoup(page_source, "html.parser")

        a_normal = page_content.findAll("li", {"class": "a-normal"})
        a_selected = page_content.findAll("li", {"class": "a-selected"})
        max_pages = len(a_normal + a_selected) - 1

        return max_pages

    def scrape_date_cost_orderid(self, order_info_) -> None:
        orders = []
        for i in order_info_:
            orders.append(i.text.strip())

        index = 0
        for i in orders:
            if index == 0:
                self.date = np.append(self.date, i)
                index += 1
            elif index == 1:
                self.cost = np.append(self.cost, i)
                index += 1
            elif index == 2:
                self.order_id = np.append(self.order_id, i)
                index = 0

    def scrape_addressee(self, addressee_info_) -> None:
        for d in addressee_info_:
            if d.find("span", {"class": "trigger-text"}) is not None:
                self.addressee = np.append(self.addressee, d.find("span", {"class": "trigger-text"}).text.strip())
            else:
                self.addressee = np.append(self.addressee, None)

    def scrape_first_page_before_progressing(self, driver: webdriver) -> None:
        time.sleep(2)
        page_source = driver.page_source
        page_content = BeautifulSoup(page_source, "html.parser")
        order_info = page_content.findAll("span", {"class": "a-color-secondary value"})
        addressee_info = page_content.findAll("div", {"class": "a-box a-color-offset-background order-info"})

        self.scrape_addressee(addressee_info)
        self.scrape_date_cost_orderid(order_info)

    def scrape_page(self, driver: webdriver, year: int, i: int) -> None:
        start_index = list(range(10, 110, 10))
        driver.get(
            self.URL(year, start_index[i])
        )
        time.sleep(2)

        data = driver.page_source
        page_content = BeautifulSoup(data, "html.parser")
        order_info = page_content.findAll("span", {"class": "a-color-secondary value"})
        addressee_info = page_content.findAll("div", {"class": "a-box a-color-offset-background order-info"})

        self.scrape_addressee(addressee_info)
        self.scrape_date_cost_orderid(order_info)

def prepare_dataset(order_data: pd.DataFrame) -> pd.DataFrame:
    def remove_euro_char(s):
        if s is None:
            return s
        else:
            return s.replace('€', '')
    locale.setlocale(locale.LC_ALL, settings_locale)
    def convert_to_nullable_value(v):
        if v is None:
            return v
        else:
            return locale.atof(v)
    order_data = order_data.loc[~order_data['Product ID'].isna()]
    order_data = order_data.set_index(['Order ID', 'Product ID'])
    #order_data.set_index("Order ID", inplace=True)

    order_data["Order Total Cost €"] = order_data["Cost €"].apply(remove_euro_char).apply(convert_to_nullable_value)
    order_data["Purchased Price €"] = order_data["Purchased Price €"].apply(remove_euro_char).apply(convert_to_nullable_value)
    order_data["Current Price €"] = order_data["Current Price €"].apply(remove_euro_char).apply(convert_to_nullable_value)
    order_data["Refound €"] = order_data["Refound €"].apply(remove_euro_char).apply(convert_to_nullable_value)
    order_data['Order Date'] = pd.to_datetime(order_data['Date'], format='%d %B %Y')
    order_data['Month Number'] = pd.DatetimeIndex(order_data['Order Date']).month
    order_data['Day'] = pd.DatetimeIndex(order_data['Order Date']).dayofweek

    day_of_week = {
        0: 'Monday',
        1: 'Tuesday',
        2: 'Wednesday',
        3: 'Thursday',
        4: 'Friday',
        5: 'Saturday',
        6: 'Sunday'
    }

    order_data["Day Of Week"] = order_data['Order Date'].dt.dayofweek.map(day_of_week)

    month = {
        1: 'January',
        2: 'February',
        3: 'March',
        4: 'April',
        5: 'May',
        6: 'June',
        7: 'July',
        8: 'August',
        9: 'September',
        10: 'October',
        11: 'November',
        12: 'December'
    }

    order_data["Month"] = order_data['Order Date'].dt.month.map(month)
    order_data["Year"] = pd.DatetimeIndex(order_data['Order Date']).year
    order_data.drop(columns=['Month Number', 'Day', 'Date'], inplace=True)

    return order_data[['Name', 'Categories', 'Purchased Price €', 'Refound €', 'Link', 'Current Price €',
                       'Order Date', 'Addressee', 'Day Of Week', 'Month', 'Year', 'Order Total Cost €']]

settings_locale = ''
if __name__ == '__main__':
    with open('config_file.yaml') as f:
        config_parm = yaml.load(f, Loader=yaml.FullLoader)
    settings_locale = config_parm['settings_locale']

    aos = AmazonOrderScraper(config_parm)
    order_data = aos.scrape_order_data(start_year=2010, end_year=2023)
    order_data.to_pickle("order_data_raw.pkl")
    order_data = prepare_dataset(order_data)
    order_data.to_pickle("order_data.pkl")
    print(order_data.head(3))

