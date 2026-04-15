"""浏览器驱动管理模块"""

from typing import Optional
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

from src.config import Settings


class BrowserDriver:
    """浏览器驱动器包装类"""
    
    def __init__(self, driver: webdriver.Chrome):
        self._driver = driver
        self._is_closed = False
    
    @property
    def driver(self) -> webdriver.Chrome:
        """获取底层 WebDriver 实例"""
        if self._is_closed:
            raise RuntimeError("BrowserDriver has been closed")
        return self._driver
    
    def get(self, url: str):
        """导航到 URL"""
        self._driver.get(url)
    
    @property
    def page_source(self) -> str:
        """获取页面源码"""
        return self._driver.page_source
    
    def quit(self):
        """关闭浏览器"""
        if not self._is_closed:
            self._driver.quit()
            self._is_closed = True
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.quit()


class DriverFactory:
    """Chrome WebDriver 工厂类"""
    
    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or Settings.get_default()
    
    def create(self) -> BrowserDriver:
        """
        创建并配置 Chrome WebDriver
        
        Returns:
            配置好的 BrowserDriver 实例
        """
        chrome_options = Options()
        
        if self.settings.browser_headless:
            chrome_options.add_argument("--headless")
        if self.settings.browser_disable_gpu:
            chrome_options.add_argument("--disable-gpu")
        if self.settings.browser_mute_audio:
            chrome_options.add_argument("--mute-audio")
        if self.settings.browser_disable_images:
            prefs = {"profile.managed_default_content_settings.images": 2}
            chrome_options.add_experimental_option("prefs", prefs)
        
        chrome_options.add_argument(self.settings.browser_user_agent)
        
        try:
            driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()),
                options=chrome_options
            )
            return BrowserDriver(driver)
        except Exception as e:
            print(f"初始化 Selenium 驱动失败：{e}")
            raise
    
    @staticmethod
    def create_default() -> BrowserDriver:
        """使用默认设置创建驱动"""
        factory = DriverFactory()
        return factory.create()
