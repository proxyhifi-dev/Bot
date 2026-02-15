
from data_provider import get_option_chain

def main() -> None:
	"""
	Main entry point for running option chain retrieval and display.
	"""
	symbol = "NSE:NIFTY50-INDEX"
	chain = get_option_chain(symbol)
	print("OPTION CHAIN RECEIVED")
	print("Total strikes:", len(chain))

if __name__ == "__main__":
	main()
