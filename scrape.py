import os
import smtplib
from email.utils import formataddr
from email.message import EmailMessage

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait

# Configuration from Environment Variables
URL = os.getenv("URL")
MARKING_ID = os.getenv("MARKING_ID")
REMEMBER_CHANGES = os.getenv("REMEMBER_CHANGES", "1") in (True, "true", "True", "1", 1)

USE_REMOTE_WEBDRIVER = os.getenv("USE_REMOTE_WEBDRIVER", "1") in (
    True,
    "true",
    "True",
    "1",
    1,
)
REMOTE_TYPE = os.getenv("REMOTE_TYPE")
REMOTE_WEBDRIVER = os.getenv("REMOTE_WEBDRIVER")

SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = os.getenv("SMTP_PORT")
SMTP_FROM = os.getenv("SMTP_FROM")
SMTP_TO = os.getenv("SMTP_TO")


### LOCK FILE ###
def read_lock():
    try:
        with open(LOCK_FILE, "r", encoding="UTF-8") as file:
            return file.read().strip()
    except FileNotFoundError:
        return ""


def write_lock(content):
    if not REMEMBER_CHANGES:
        pass

    existing_content = read_lock()
    if content not in existing_content:
        content = existing_content + content
    else:
        pass
    with open(LOCK_FILE, "w", encoding="UTF-8") as file:
        file.write(content)


def delete_lock():
    if not REMEMBER_CHANGES:
        pass

    try:
        os.remove(LOCK_FILE)
    except FileNotFoundError:
        pass


LOCK_FILE = ".scrplock"
### / LOCK FILE ###


### SELENIUM DRIVERS ###
def get_local_chrome_driver():
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service as ChromeService
    from webdriver_manager.chrome import ChromeDriverManager

    options = Options()
    options.add_argument("--headless")

    return webdriver.Chrome(
        service=ChromeService(ChromeDriverManager().install(), options=options)
    )

def get_local_firefox_driver():
    from selenium.webdriver.firefox.options import Options
    from selenium.webdriver.firefox.service import Service as FirefoxService
    from webdriver_manager.firefox import GeckoDriverManager

    options = Options()
    options.add_argument("-headless")

    return webdriver.Firefox(
        service=FirefoxService(GeckoDriverManager().install(), options=options)
    )

def get_remote_chrome_driver():
    from selenium.webdriver.chrome.options import Options
    
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--no-sandbox')

    return webdriver.Remote(command_executor=REMOTE_WEBDRIVER, options=options)

def get_remote_firefox_driver():
    from selenium.webdriver.firefox.options import Options
    
    options = Options()
    options.add_argument('-headless')

    return webdriver.Remote(command_executor=REMOTE_WEBDRIVER, options=options)

### / SELENIUM DRIVERS ###


def lambda_handler(event, context):

    print("Starting check...")
    
    if USE_REMOTE_WEBDRIVER and REMOTE_TYPE == 'firefox':
        driver = get_remote_firefox_driver()
    elif not USE_REMOTE_WEBDRIVER and REMOTE_TYPE == 'firefox':
        driver = get_local_firefox_driver()
    elif USE_REMOTE_WEBDRIVER and REMOTE_TYPE == 'chrome':
        driver = get_remote_chrome_driver()
    elif not USE_REMOTE_WEBDRIVER and REMOTE_TYPE == 'chrome':
        driver = get_local_chrome_driver()
    else:
        raise Exception("No driver")

    print(f"Calling {[URL]}...")
    driver.get(URL)
    WebDriverWait(driver, 15).until(
        lambda driverx: driverx.execute_script("return document.readyState")
        == "complete"
    )

    if driver.page_source:
        soup = BeautifulSoup(driver.page_source, "html.parser")
        try:
            driver.quit()
            
            parent_div = soup.find("div", {"class": "product-list"})
            target_divs = parent_div.find_all("div", {"class": "product-tile-set"})
            marker_not_found = True

            for idx, div in enumerate(target_divs):
                if div.get("id") == MARKING_ID:
                    if idx == 0:
                        print("No products detected")
                        delete_lock()
                    marker_not_found = False
                    break

                else:
                    url = div.get("data-pdp-url")
                    name = div.find("span", class_="description").find("a").text.strip()

                    urls = read_lock()
                    if REMEMBER_CHANGES and url in urls:
                        print("New product still up, no change detected")
                    else:
                        print(f"Product found: {name}")
                        print(f"\turl: [{url}]")
                        # print(div)
                        body_format = f"{url}\r\n\r\n*****\r\n{div}\r\n*****"
                        send_email(f"*** COSTCO Product: {name}", body_format)
                        write_lock(url)

            if marker_not_found:
                print(f"Marking product not found")
                send_email(
                    f"ERROR - COSTCO Product Up - Marking product not found",
                    f"Update tool: {URL}",
                )
        except Exception as e:
            print(e)
            print("Layout change, need to re-configure")
            send_email(
                f"ERROR - COSTCO Product Up - Layout change",
                f"Update tool: {URL}",
            )
    else:
        print(f"Failed to fetch the webpage, status code: {response.status_code}")


def send_email(subject, body):
    try:
        msg = EmailMessage()
        msg["From"] = formataddr(("SCRPR Tool", SMTP_FROM))
        msg["To"] = SMTP_TO
        msg["Subject"] = subject
        msg.set_content(body)

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(msg)
            print("Email sent successfully!")

    except Exception as e:
        print(f"Failed to send email: {e}")


# If running this script directly, for testing purposes
if __name__ == "__main__":
    lambda_handler(None, None)
