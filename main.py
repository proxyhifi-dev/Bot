from data_provider import get_option_chain

symbol = "NSE:NIFTY50-INDEX"

chain = get_option_chain(symbol)

print("OPTION CHAIN RECEIVED")
print("Total strikes:", len(chain))
