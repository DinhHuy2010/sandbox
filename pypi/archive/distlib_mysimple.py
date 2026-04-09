from distlib.locators import PyPIJSONLocator

locator = PyPIJSONLocator("https://pypi.org/pypi")
d = locator.locate("pip")
