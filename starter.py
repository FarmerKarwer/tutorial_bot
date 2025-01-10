import sys
import os
import json
import traceback
import argparse

# Add the src folder to sys.path
sys.path.append(os.path.abspath('./src'))

from src.index import handler, handler_long

def main():
    parser = argparse.ArgumentParser(description="Select the polling method.")
    parser.add_argument(
        '--handler', 
        choices=['short', 'long'], 
        default='long', 
        help="Choose 'short' for short polling or 'long' for long polling (default: 'long')"
    )
    args = parser.parse_args()
    try:
        if args.handler == 'short':
            use_handler = handler()
            print(use_handler['message'])
        else:
            use_handler = handler_long()
    except Exception as e:
        print("Something Went Wrong", e)
        traceback.print_exc()

if __name__ == "__main__":
    main()
    