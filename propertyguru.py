import json
import time
import pymysql
import re
import csv
import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver import ActionChains
from selenium.common import NoSuchElementException
from selenium.common.exceptions import WebDriverException, TimeoutException

from appconfig_server import AppConfig
from logger import main_logger

# Global variables
driver = None


def setup_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--disable-application-cache")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("disable-infobars")
    options.set_capability("goog:loggingPrefs", {"performance": "ALL"})
    options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    if AppConfig.USE_HEADLESS:
        options.add_argument("--headless=new")
    else:
        options.add_argument("--start-maximized")

    try:
        driver = webdriver.Chrome(options=options)
        driver.execute_cdp_cmd("Page.enable", {})
        driver.execute_cdp_cmd("Runtime.enable", {})
        driver.execute_cdp_cmd("Network.enable", {})
        return driver
    except Exception as e:
        LOG.info(f"====================== Driver setup failed =======================\n Details: {e}", exc_info=True)
        return False

def __click_element__(driver, element, use_java=False):
    if use_java:
        driver.execute_script("arguments[0].click();", element)
    else:
        try:
            driver.execute_script("arguments[0].scrollIntoView();", element)
            element.click()
        except:
            ActionChains(driver).move_to_element(element).click().perform()

def select_state_filter(driver, state):
    try:
        if state.strip() == "" or state is None:
            return True
        
        search_by_state = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "search-typeahead-item-0"))
        )
        search_by_state.click()
        time.sleep(1)
        filter_input = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'input[placeholder="Filter State Name"]'))
        )
        time.sleep(1)
        filter_input.clear()
        filter_input.send_keys(state)
        time.sleep(3)
        # filter_input.send_keys(Keys.ENTER)
        state_result = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, '.items > ul > li:first-child'))
        )
        # state_result = driver.find_element(By.CSS_SELECTOR, 'ul.hui-list li.hui-list-item')
        __click_element__(driver, state_result)
        time.sleep(5)
        apply_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, '.hui-modal-footer .btn-primary'))
        )
        apply_button.click()
        return True
        
    except Exception as e:
        LOG.exception(f"Error selecting state filter: {e}")
        return False

def select_tab(driver, tab):
    try:
        tab = tab.upper()
        if tab not in ['BUY', 'RENT']:
            tab = 'BUY'
        
        tab_selector = '[data-rr-ui-event-key="buy"]' if tab == 'BUY' else '[data-rr-ui-event-key="rent"]'
        tab_element = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, tab_selector))
        )
        __click_element__(driver, tab_element)
        time.sleep(2)
        return True
        
    except Exception as e:
        LOG.error(f"Error selecting tab '{tab}': {e}")
        return False
    
def handle_login(driver):
    try:
        login_button = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[da-id="mega-menu-navbar-login-button"]'))
        )
        LOG.info(f"Login button text: {login_button.text}")
        if login_button.text == "Login":
            __click_element__(driver, login_button)
            time.sleep(2)
            email_input = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'input[da-id="email-fld"]'))
            )
            email_input.clear()
            time.sleep(1)
            email_input.send_keys(AppConfig.PROPERTYGURU_EMAIL)
            time.sleep(0.5)
            email_input.send_keys(Keys.ENTER)
            time.sleep(3)
            password_input = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'input[da-id="password-fld"]'))
            )
            password_input.clear()
            password_input.send_keys(AppConfig.PROPERTYGURU_PASSWORD)
            time.sleep(0.5)
            password_input.send_keys(Keys.ENTER)
            time.sleep(5)
    except TimeoutException:
        LOG.info("Login button not found, possibly already logged in.")

def scrape_all_pages(driver):
    all_links = set()
    page_num = 1
    while True:
        # Wait for results to load
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'div.search-result-root[da-id="search-result-root"]'))
        )
        link_elements = driver.find_elements(By.CSS_SELECTOR, 'a.listing-card-link')
        links = [el.get_attribute("href") for el in link_elements]
        LOG.info(f"Page {page_num}: Found {len(links)} listing links")
        all_links.update(links)

        # Try to find the "Next" button (not disabled)
        try:
            next_btn = driver.find_element(By.CSS_SELECTOR, 'a.page-link[da-id="hui-pagination-btn-next"]')
            parent_li = next_btn.find_element(By.XPATH, './ancestor::li[contains(@class, "page-item")]')
            if "disabled" in parent_li.get_attribute("class"):
                break  # No more pages
            # Click next and wait for page to load
            __click_element__(driver, next_btn)
            time.sleep(5)
            page_num += 1
        except Exception:
            LOG.info(f"No more pages or next button not found")
            break
    return list(all_links)

def handle_detail_page(driver, url):
    try:
        driver.get(url)
        # Find the script tag by its id
        script_tag = driver.find_element(By.ID, "__NEXT_DATA__")

        # Get the raw JSON text inside the script tag
        json_text = script_tag.get_attribute("innerHTML")
        data = json.loads(json_text)
        # Navigate to the correct data structure
        page_data = data.get("props", {}).get("pageProps", {}).get("pageData", {}).get("data", {})

        # Extract property info
        property_info = page_data.get("propertyOverviewData", {}).get("propertyInfo", {})
        listing_data = page_data.get("listingData", {})
        contact_agent_card = page_data.get("contactAgentData", {}).get("contactAgentCard", {})

        details = {
            "agency_name": contact_agent_card.get("agency", {}).get("name", ""),
            "agent_name": listing_data.get("agent", {}).get("name", ""),
            "agent_license_number": listing_data.get("agent", {}).get("licenseNumber", ""),
            "agent_mobile": listing_data.get("agent", {}).get("mobile", ""),
            "agent_phone": listing_data.get("agent", {}).get("phone", ""),
            "title": property_info.get("title", ""),
            "address": property_info.get("fullAddress", ""),
            # "price": listing_data.get("pricePretty") or property_info.get("price", {}).get("amount"),
            "price": listing_data.get("price", 0.0),
            'url': url
        }        
        LOG.info(f"Extracted details: {details}")
        return details
    except Exception as e:
        LOG.error(f"Error handling detail page {url}: {e}")
        return None

def insert_into_db(details, keyword, tab, state):
    try:
        connection = pymysql.connect(
            host=AppConfig.MYSQL_SERVER,
            user=AppConfig.MYSQL_USER,
            passwd=AppConfig.MYSQL_PASSWORD,
            db=AppConfig.MYSQL_DATABASE,
            connect_timeout=20,
            read_timeout=60
        )
        with connection:
            with connection.cursor() as cursor:
                sql = """
                    INSERT INTO propertyguru (
                        url, title, address, price, agency_name, agent_name, agent_license_number,
                        agent_mobile, agent_phone, keyword, tab, state, created_at, updated_at
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, NOW(), NOW()
                    )
                    ON DUPLICATE KEY UPDATE
                        title=VALUES(title),
                        address=VALUES(address),
                        price=VALUES(price),
                        agency_name=VALUES(agency_name),
                        agent_name=VALUES(agent_name),
                        agent_license_number=VALUES(agent_license_number),
                        agent_mobile=VALUES(agent_mobile),
                        agent_phone=VALUES(agent_phone),
                        keyword=VALUES(keyword),
                        tab=VALUES(tab),
                        state=VALUES(state),
                        updated_at=NOW()
                """
                # Clean price to decimal
                # price_str = details.get("price", "0").replace("RM", "").replace(",", "").strip()
                # try:
                #     price = float(price_str)
                # except ValueError:
                #     price = 0.0

                cursor.execute(sql, (
                    details.get("url"),
                    details.get("title"),
                    details.get("address"),
                    details.get("price"),
                    details.get("agency_name"),
                    details.get("agent_name"),
                    details.get("agent_license_number"),
                    details.get("agent_mobile"),
                    details.get("agent_phone"),
                    keyword,
                    tab,
                    state
                ))
                connection.commit()
                LOG.info(f"Inserted/Updated record for URL: {details.get('url')}")
    except Exception as e:
        LOG.error(f"Database error for URL {details.get('url')}: {e}")

def export_to_csv(details, keyword, tab, state, filename=None):
    def safe(s):
        return re.sub(r'[^A-Za-z0-9]+', '_', str(s)).strip('_')
    if filename is None:
        # timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"propertyguru_{safe(keyword)}_{safe(tab)}_{safe(state)}.csv"

    fieldnames = [
        "url", "title", "address", "price", "agency_name", "agent_name", "agent_license_number",
        "agent_mobile", "agent_phone", "keyword", "tab", "state"
    ]
    row = {
        "url": details.get("url"),
        "title": details.get("title"),
        "address": details.get("address"),
        "price": details.get("price"),
        "agency_name": details.get("agency_name"),
        "agent_name": details.get("agent_name"),
        "agent_license_number": details.get("agent_license_number"),
        "agent_mobile": details.get("agent_mobile"),
        "agent_phone": details.get("agent_phone"),
        "keyword": keyword,
        "tab": tab,
        "state": state
    }
    write_header = False
    try:
        # Check if file exists and is empty
        try:
            with open(filename, "r", encoding="utf-8") as f:
                if not f.readline():
                    write_header = True
        except FileNotFoundError:
            write_header = True

        with open(filename, "a", newline='', encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            if write_header:
                writer.writeheader()
            writer.writerow(row)
    except Exception as e:
        LOG.error(f"CSV export error for URL {details.get('url')}: {e}")

def main(keyword="ativo suites", tab='BUY', state=''):
    global driver

    def safe(s):
        return re.sub(r'[^A-Za-z0-9]+', '_', str(s)).strip('_')
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"propertyguru_{safe(keyword)}_{safe(tab)}_{safe(state)}_{timestamp}.csv"
    try:
        driver = setup_driver()
        if not driver:
            return
        url = "https://www.propertyguru.com.my/"
        driver.get(url)
        time.sleep(3)

        # Detect Cloudflare human verification
        if "Verify you are human" in driver.page_source or "cf-turnstile-response" in driver.page_source:
            LOG.warning("Cloudflare human verification detected. Please solve it manually in the browser window.")
            input("Press Enter after you have completed the verification...")  # Wait for user to solve

            # Reload the page after verification
            driver.get(url)
            time.sleep(3)

        handle_login(driver)

        # select tab
        select_tab(driver, tab)
        time.sleep(2)

        # click input keyword box
        search_input = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'input[da-id="search-box-input"]'))
        )
        search_input.click()
        time.sleep(1)
        search_input.clear()

        if state:
            # select_state_filter(driver, state)
            search_input.send_keys(state)
            time.sleep(2)
            search_input.send_keys(Keys.DOWN)
            time.sleep(1)
            search_input.send_keys(Keys.ENTER)
        else:
            search_input.send_keys(keyword)
        time.sleep(2)
        search_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[da-id="search-button"]'))
        )
        search_button.click()
        time.sleep(5)
        all_links = scrape_all_pages(driver)
        LOG.info(f"Total unique listing links found: {len(all_links)}")
        # log all links
        for link in all_links:
            LOG.info(f"Listing link: {link}")
            details = handle_detail_page(driver, link)
            if details:
                export_to_csv(details, keyword, tab, state, filename=filename)

            time.sleep(15)

    except Exception as e:
        LOG.exception(f"Error: {e}")
    finally:
        try:
            driver.quit()
        except Exception:
            pass

if __name__ == '__main__':
    LOG = main_logger("PropertyGuru")
    main(keyword="ativo suites", tab='BUY', state='')
# chrome.exe --remote-debugging-port=9222 --user-data-dir="C:\ChromeDebug"
