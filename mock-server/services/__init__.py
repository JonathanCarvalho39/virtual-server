from services.folder_scanner import FolderScanner
from services.scenario_loader import ScenarioLoader
from config import API_DIR

scanner = FolderScanner(API_DIR)
loader = ScenarioLoader()
