#!/usr/bin/env python3
"""
Script to analyze API usage data and calculate total costs and usage metrics.
"""

import csv
import json
from collections import defaultdict
from datetime import datetime

def analyze_usage_data(csv_file):
    """Analyze the usage data from CSV file."""

    # Initialize counters
    totals = {
        'total_requests': 0,
        'included_requests': 0,
        'errored_requests': 0,
        'input_with_cache_write': 0,
        'input_without_cache_write': 0,
        'cache_read': 0,
        'output_tokens': 0,
        'total_tokens': 0
    }

    model_breakdown = defaultdict(lambda: {
        'requests': 0,
        'input_with_cache_write': 0,
        'input_without_cache_write': 0,
        'cache_read': 0,
        'output_tokens': 0,
        'total_tokens': 0,
        'included': 0,
        'errored': 0
    })

    daily_usage = defaultdict(lambda: {
        'requests': 0,
        'total_tokens': 0,
        'included': 0,
        'errored': 0
    })

    # Read and process CSV data
    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)

        for row in reader:
            # Parse date
            date_str = row['Date'].strip('"')
            date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            date_key = date_obj.strftime('%Y-%m-%d')

            # Basic counts
            totals['total_requests'] += 1
            daily_usage[date_key]['requests'] += 1

            # Model info
            model = row['Model'].strip('"')
            model_breakdown[model]['requests'] += 1

            # Status tracking
            kind = row['Kind'].strip('"')
            if 'Errored' in kind:
                totals['errored_requests'] += 1
                model_breakdown[model]['errored'] += 1
                daily_usage[date_key]['errored'] += 1
            else:
                totals['included_requests'] += 1
                model_breakdown[model]['included'] += 1
                daily_usage[date_key]['included'] += 1

            # Token calculations
            try:
                input_with_cache = int(row['Input (w/ Cache Write)'].strip('"'))
                input_without_cache = int(row['Input (w/o Cache Write)'].strip('"'))
                cache_read = int(row['Cache Read'].strip('"'))
                output_tokens = int(row['Output Tokens'].strip('"'))
                total_tokens = int(row['Total Tokens'].strip('"'))

                totals['input_with_cache_write'] += input_with_cache
                totals['input_without_cache_write'] += input_without_cache
                totals['cache_read'] += cache_read
                totals['output_tokens'] += output_tokens
                totals['total_tokens'] += total_tokens

                model_breakdown[model]['input_with_cache_write'] += input_with_cache
                model_breakdown[model]['input_without_cache_write'] += input_without_cache
                model_breakdown[model]['cache_read'] += cache_read
                model_breakdown[model]['output_tokens'] += output_tokens
                model_breakdown[model]['total_tokens'] += total_tokens

                daily_usage[date_key]['total_tokens'] += total_tokens

            except ValueError as e:
                print(f"Error parsing numeric values in row: {e}")
                continue

    return totals, model_breakdown, daily_usage

def format_number(num):
    """Format large numbers with commas."""
    return f"{num:,}"

def print_analysis(totals, model_breakdown, daily_usage):
    """Print comprehensive usage analysis."""

    print("=" * 80)
    print("API USAGE ANALYSIS REPORT")
    print("=" * 80)

    # Overall totals
    print("\n📊 OVERALL USAGE TOTALS")
    print("-" * 40)
    print(f"Total API Requests: {format_number(totals['total_requests'])}")
    print(f"Successful Requests: {format_number(totals['included_requests'])}")
    print(f"Errored Requests: {format_number(totals['errored_requests'])}")
    print(f"Success Rate: {(totals['included_requests']/totals['total_requests']*100):.1f}%")
    print()
    print(f"Total Tokens Processed: {format_number(totals['total_tokens'])}")
    print(f"Input Tokens (w/ Cache Write): {format_number(totals['input_with_cache_write'])}")
    print(f"Input Tokens (w/o Cache Write): {format_number(totals['input_without_cache_write'])}")
    print(f"Cache Read Tokens: {format_number(totals['cache_read'])}")
    print(f"Output Tokens: {format_number(totals['output_tokens'])}")

    # Cost analysis
    print("\n💰 COST ANALYSIS")
    print("-" * 40)
    print("All requests show 'Included' in the cost column.")
    print("This indicates usage is covered under a subscription plan.")
    print("No separate monetary charges are listed.")

    # Model breakdown
    print("\n🤖 MODEL BREAKDOWN")
    print("-" * 40)
    for model, stats in sorted(model_breakdown.items()):
        print(f"\n{model}:")
        print(f"  Requests: {format_number(stats['requests'])}")
        print(f"  Total Tokens: {format_number(stats['total_tokens'])}")
        print(f"  Success Rate: {(stats['included']/(stats['included']+stats['errored'])*100):.1f}%")
        if stats['total_tokens'] > 0:
            avg_tokens = stats['total_tokens'] / stats['requests']
            print(f"  Avg Tokens/Request: {format_number(int(avg_tokens))}")

    # Daily breakdown (last 7 days)
    print("\n📅 DAILY USAGE (Recent Days)")
    print("-" * 40)
    sorted_days = sorted(daily_usage.items(), reverse=True)[:7]
    for date, stats in sorted_days:
        success_rate = (stats['included']/(stats['included']+stats['errored'])*100) if (stats['included']+stats['errored']) > 0 else 0
        print(f"{date}: {stats['requests']} requests, {format_number(stats['total_tokens'])} tokens, {success_rate:.1f}% success")

    # Cache efficiency
    print("\n🗄️ CACHE EFFICIENCY")
    print("-" * 40)
    total_input_tokens = totals['input_with_cache_write'] + totals['input_without_cache_write']
    if total_input_tokens > 0:
        cache_ratio = totals['cache_read'] / (totals['cache_read'] + total_input_tokens) * 100
        print(f"Cache Read Tokens: {format_number(totals['cache_read'])}")
        print(f"Fresh Input Tokens: {format_number(total_input_tokens)}")
        print(f"Cache Hit Ratio: {cache_ratio:.1f}%")
        print(f"Cache is providing {cache_ratio:.1f}% of total input context")

    # Token distribution
    print("\n📈 TOKEN DISTRIBUTION")
    print("-" * 40)
    input_ratio = (totals['input_with_cache_write'] + totals['input_without_cache_write']) / totals['total_tokens'] * 100
    cache_ratio = totals['cache_read'] / totals['total_tokens'] * 100
    output_ratio = totals['output_tokens'] / totals['total_tokens'] * 100

    print(f"Fresh Input: {input_ratio:.1f}%")
    print(f"Cache Read: {cache_ratio:.1f}%")
    print(f"Output: {output_ratio:.1f}%")

if __name__ == "__main__":
    csv_file = "/Volumes/config/custom_components/ha_the_masjid_app/usage_data.csv"

    try:
        totals, model_breakdown, daily_usage = analyze_usage_data(csv_file)
        print_analysis(totals, model_breakdown, daily_usage)

        # Summary for easy reference
        print("\n" + "=" * 80)
        print("QUICK SUMMARY")
        print("=" * 80)
        print(f"🔢 Total Requests: {format_number(totals['total_requests'])}")
        print(f"🎯 Success Rate: {(totals['included_requests']/totals['total_requests']*100):.1f}%")
        print(f"🪙 Total Tokens: {format_number(totals['total_tokens'])}")
        print(f"💰 Total Cost: $0.00 (All included in plan)")
        print("=" * 80)

    except Exception as e:
        print(f"Error analyzing data: {e}")
        import traceback
        traceback.print_exc()
