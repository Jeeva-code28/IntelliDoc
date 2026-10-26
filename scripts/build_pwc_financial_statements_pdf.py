import pymupdf
from pathlib import Path

def generate_pwc_pdf():
    pdf_path = Path("data") / "pwc_financial_statements_september_2020.pdf"
    pdf_path.parent.mkdir(parents=True, exist_ok=True)

    doc = pymupdf.open()

    pages_data = [
        # Page 1
        ("Basic understanding of a company's financial statements\nSeptember 2020\nPwC", 
         ["Basic understanding of a company's financial statements", "PricewaterhouseCoopers (PwC) Executive Training", "September 2020"]),
        
        # Page 2
        ("Table of contents",
         ["Table of contents",
          "What are financial statements? .................... Page 3",
          "Balance sheet ..................................... Page 5",
          "Income statement ................................. Page 16",
          "Cashflow statement ............................... Page 24"]),
        
        # Page 3
        ("What are financial statements?",
         ["Section 1: What are financial statements?", "PwC | Basic Understanding of a Company's Financials"]),
        
        # Page 4
        ("The financial statements",
         ["The financial statements",
          "Financial statements are written records that illustrates the business activities and the financial performance of a company. In most cases they are audited to ensure accuracy for tax, financing, or investing purposes.",
          "A methodically work through of the three financial statements in order to assess the Financial health of a company.",
          "1. Balance Sheet: Statement of financial position. A snapshot at a point in time. On the top half you have the company's assets and on the bottom half its liabilities and Shareholders' Equity (or Net Worth). Assets and liabilities are listed in order of liquidity and separated between current and non-current.",
          "2. Income Statement: Statement of operation/profit and loss. Covers a period of time, such as a quarter or year. Illustrates profitability from an accrual and matching perspective. Starts with revenue and after deducting expenses derives net income.",
          "3. Statement of Cash Flows: Examines the cash position of the company. Answers how much cash goes to creditors and shareholders and whether enough is retained for investment and growth. Has 3 components: cash from operations, cash used in investing, and cash from financing."]),
        
        # Page 5
        ("Balance sheet",
         ["Section 2: Balance sheet", "PwC | Basic Understanding of a Company's Financials"]),
        
        # Page 6
        ("Simplified Balance Sheet",
         ["Balance sheet: 3 main categories: Assets, Liabilities, Equity.",
          "Simplified Balance Sheet:",
          "Assets:",
          "- Current assets: Cash $20,000 | Accounts receivable $3,000 | Inventory $60,000 | Prepaid expenses $11,000 | Total current assets $94,000",
          "- Non current assets: Property plant & equipment $110,000 | Intangible assets $10,000 | Total non current assets $120,000",
          "- Total assets: $214,000",
          "Liabilities & Equity:",
          "- Current liabilities: Accounts payable $2,000 | Accrued expenses $1,000 | Total current liabilities $3,000",
          "- Non current liabilities: Bank loan $100,000 | Total non current liabilities $11,000 (other) + $100,000 bank loan",
          "- Shareholder equity: Common shares $89,000 | Retained Earnings $11,000",
          "- Total liabilities and shareholders equity: $214,000",
          "Current vs Non-current classification:",
          "Current assets expected to be converted into cash in less than 1 year (accounts receivable, inventory).",
          "Current liabilities will be paid in less than 1 year (trade accounts payable).",
          "Non-current assets held greater than 1 year (property, plant, equipment).",
          "Non-current liabilities repayment terms longer than 1 year (bank loans over 5 years)."]),
        
        # Page 7
        ("Illustrative balance sheet (assets)",
         ["Illustrative balance sheet (assets)",
          "Current Assets: Inventories (2018: 2,199,273 | 2019: 3,225,686), Receivables and prepayments (2018: 2,302,693 | 2019: 2,585,519), Investment securities (2018: 269,530 | 2019: 130,385), Cash and short-term deposits (2018: 3,968,075 | 2019: 3,974,545). Total Current Assets (2018: 8,739,571 | 2019: 9,916,135).",
          "Non-Current Assets: Property, plant and equipment (2018: 6,775,727 | 2019: 6,724,278), Investment in associates (2019: 593,961), Loans receivable (2019: 165,545), Investment securities (2018: 215,760 | 2019: 379,060). Total Non-Current Assets (2018: 6,991,487 | 2019: 7,862,844).",
          "Total Assets: 2018: 15,731,058 | 2019: 17,778,979."]),

        # Page 8
        ("Cash and investments",
         ["Cash and investments",
          "A company will hold external investments for two reasons: 1. Excess cash, 2. Accumulating cash to make a large purchase.",
          "Internal investments: short term (less than 1 year) and long term (more than 1 year).",
          "External investments: Investments in equity or debt instruments held for capital gain and/or income.",
          "Investment in subsidiaries, associates, and joint ventures."]),

        # Page 9
        ("Other assets",
         ["Other assets: Goodwill, Intangible Assets, Unearned / Deferred Revenue",
          "Goodwill: Non-current asset. Company has intangible value e.g. brand, customers, intellectual capital. Arises if a company is purchased for more than the fair value of net assets acquired: Purchase price X minus Fair value of net assets acquired (X) = Goodwill X.",
          "Intangible Asset: Items of value that are used to generate revenues and have no physical substance (Trademarks, Patents, Copyrights).",
          "Unearned/Deferred Revenue: Arises when a company sells something it has not yet delivered e.g. licenses, subscriptions. Example: 12 month subscription sold for $1,200 in January: Jan Earned $100, Unearned $1,100; Mar Earned $300, Unearned $900; Jun Earned $600, Unearned $600; Sep Earned $900, Unearned $300; Dec Earned $1,200, Unearned $0."]),

        # Page 10
        ("Illustrative balance sheet (liabilities)",
         ["Illustrative balance sheet (liabilities)",
          "Current Liabilities: Will be paid in less than 1 year. Trade and other payables (2018: 3,873,904 | 2019: 3,336,064), Short-term borrowings (2018: 376,686 | 2019: 485,724), Taxation payable (2018: 362,940 | 2019: 444,969). Total Current Liabilities (2018: 4,613,530 | 2019: 4,266,757).",
          "Non-Current Liabilities: Repayment terms longer than 1 year. Deferred tax liabilities (2018: 257,430 | 2019: 213,511), Borrowings (2018: 2,169,937 | 2019: 2,213,130). Total Non-Current Liabilities (2018: 2,427,367 | 2019: 2,426,641).",
          "Total Liabilities: 2018: 7,040,897 | 2019: 6,693,398."]),

        # Page 11
        ("Other liabilities",
         ["Other liabilities: Commitments and Contingencies",
          "Commitments: Future obligations that a company agrees to (e.g. New buildings, Leasehold improvements, Building improvements).",
          "Contingencies: Liabilities that may or may not happen, depending on circumstance (e.g. lawsuit). The liability must be recorded if: 1. A loss will be suffered in the future, 2. The loss amount can be reasonably estimated. If not, disclose in notes.",
          "Rule: Contingent gains are NEVER recorded in financial statements."]),

        # Page 12
        ("Illustrative balance sheet (statement of shareholder's equity)",
         ["Statement of Changes in Equity / Shareholder's Equity",
          "Share capital: 2018: 1,192,647 | 2019: 1,192,647",
          "Capital reserve: 2018: 119,946 | 2019: 130,832",
          "Translation reserve: 2018: 30,086 | 2019: 29,048",
          "Retained earnings: 2018: 7,347,482 | 2019: 9,733,054",
          "Total Equity: 2018: 8,690,161 | 2019: 11,085,581",
          "Total Liabilities and Equity: 2018: 15,731,058 | 2019: 17,778,979."]),

        # Page 13
        ("Common vs preferred shares",
         ["Common vs Preferred shares",
          "Authorised shares: The total number of shares a company can sell (4,000,000,000 ordinary stock units).",
          "Outstanding (Issued) shares: The total number of shares a company has sold/issued (3,750,000,000 stock units).",
          "Common shares: 1. Allow for participation in profits (dividends), 2. Voting rights (one vote per share), 3. Residual claim upon dissolution.",
          "Preferred shares: 1. Fixed dividend (may accumulate before common dividends), 2. Priority over common shares, 3. Viewed as debt with tax disadvantage (dividends do not reduce taxable income)."]),

        # Page 14
        ("Aspects of the equity",
         ["Aspects of Equity: Contributed Surplus and Other Comprehensive Income (OCI)",
          "Contributed Surplus: Example 180,000 shares sold at 40 cents each with 25 cents par value. Paid-up share capital = 180,000 x 25c = $45,000. Contributed surplus = 180,000 x 15c = $27,000.",
          "Other comprehensive income (OCI): Certain company gains and losses not recorded through income statement e.g. unrealised gains/losses on investments and hedging instruments."]),

        # Page 15
        ("Understanding the income statement and cash flow",
         ["Section 3: Understanding the income statement and cash flow", "PwC | Basic Understanding of a Company's Financials"]),

        # Page 16
        ("Income statement",
         ["Income statement overview", "PwC | Basic Understanding of a Company's Financials"]),

        # Page 17
        ("Income Statement Structure",
         ["The Income statement has 3 main sections:",
          "1. Revenues",
          "2. Expenses",
          "3. Profit or loss"]),

        # Page 18
        ("Single step vs multi-step income statements",
         ["Single step vs multi-step income statements",
          "Single Step format: Total Revenue (+) plus Gains (+) minus Cost of Goods Sold (-) minus Selling, General & Administrative (-) minus Losses (-) minus Other Expenses (-) minus Income taxes (-) = Net Income.",
          "Multiple Step format: Revenue (+) minus Cost of Goods Sold (-) = Gross Profit; Gross Profit minus Selling, General & Administrative (-) = Operating Income; Operating Income plus Gains (+) minus Losses (-) minus Other Expenses (-) = Pre-tax Income; Pre-tax Income minus Income taxes (-) = Net Income."]),

        # Page 19
        ("The Illustrative income statement",
         ["Illustrative Income Statement (Consolidated Statement of Comprehensive Income for Wisynco Group Limited):",
          "Revenue: 2018: 24,544,049 | 2019: 28,412,414",
          "Cost of sales: 2018: (15,421,144) | 2019: (17,878,208)",
          "Gross Profit: 2018: 9,122,905 | 2019: 10,534,206",
          "Operating Profit: 2018: 2,845,778 | 2019: 3,599,937",
          "Profit before Taxation: 2018: 2,765,204 | 2019: 3,496,742",
          "Net Profit: 2018: 2,292,925 | 2019: 2,929,322",
          "Earnings Per Stock Unit (EPS): 2018: $0.62 | 2019: $0.78."]),

        # Page 20
        ("Cost of sales",
         ["Cost of sales or Cost of Goods Sold (COGS):",
          "May be shown as summarised line item or broken down into expense items:",
          "1. Direct Materials: Materials used in manufacturing.",
          "2. Direct Labor: Professional services delivered or wages directly producing goods.",
          "3. Direct Overhead: Production of goods or services overhead costs."]),

        # Page 21
        ("Selling, general and administrative expenses",
         ["Selling, general and administrative expenses (SG&A):",
          "Contains a large number of expense items such as:",
          "- Advertising and promotion cost",
          "- Legal, Insurance and accounting expenses",
          "- Office supplies",
          "- Other related administrative expenses"]),

        # Page 22
        ("Gains and losses",
         ["Gains and losses:",
          "May appear separately or grouped under 'other income or expenses' incidental to operations:",
          "- Sale of Investments",
          "- Foreign exchange translations",
          "- Financial Instrument transactions"]),

        # Page 23
        ("Other aspects of the Income Statement",
         ["Other aspects of the Income Statement:",
          "Other comprehensive income (OCI): Gains and losses not recorded through the income statement, including unrealised gains and losses on investments and hedging instruments."]),

        # Page 24
        ("Cashflow statement",
         ["Section 4: Cashflow statement", "PwC | Basic Understanding of a Company's Financials"]),

        # Page 25
        ("The cash flow statement",
         ["The Cash Flow Statement demonstrates where cash is generated and used in the business across 3 pillars:",
          "1. Operating activities: Day-to-day business operations. Revenues and expenses collected and paid during the year. Depreciation and amortisation are NOT included (added back).",
          "2. Investing activities: Non-current assets that support the business (Property, plant and equipment, business acquisitions).",
          "3. Financing activities: Transactions regarding shares or debt. Company raises funds by borrowing or issuing shares."]),

        # Page 26
        ("Statement of Cash Flows Structure",
         ["Statement of Cash Flows: Activity-based flow:",
          "Opening cash balance -> Operating transactions + Investing transactions + Financing transactions = Total cash transactions -> Closing cash balance."]),

        # Page 27
        ("Direct method vs Indirect method",
         ["Direct method vs Indirect method of cash flow from operating activities:",
          "Direct Method: Starts with cash transactions. Transactions are separated into cash received (from customers) and cash paid (to suppliers, employees).",
          "Indirect Method: Starts with net income. Non-cash adjustments are added back (depreciation, amortisation) and changes in working capital balances are adjusted."]),

        # Page 28
        ("Key elements in a cash flow statement",
         ["Key elements in a cash flow statement:",
          "- Net cash provided by operating activities: Represents operating 'lifeblood' of business after paying necessary outgoings for financing and tax.",
          "- Changes in working capital: Shows whether business is absorbing funds for working capital or releasing them.",
          "- PPE Investment: Companies must invest in PPE to maintain productive capacity. Downward trend indicates declining company.",
          "- Financing requirement/surplus: Shows whether internally generated funds are sufficient to cover investments in fixed assets and business acquisitions."]),

        # Page 29
        ("The Full Disclosure Principle",
         ["The Full Disclosure Principle:",
          "Notes are provided to allow the reader of financial statements to understand and make judgements of financial activities of the company."]),

        # Page 30
        ("Three Key Financial Statements Notes",
         ["Three Key Financial Statements Notes:",
          "1. Significant Accounting Policies: Company accounting standards, inventory valuation, financial instruments, revenue recognition, PP&E amortization.",
          "2. Direct Information: Breakdown of investment types, debt and financial instruments, inventory, PP&E, intangible assets, income taxes.",
          "3. Indirect Information: Commitments, contingencies, stock-based compensation plans. Helps provide full financial picture."]),

        # Page 31
        ("Ratio Analysis",
         ["Ratio Analysis: Cornerstone of fundamental equity analysis gaining insight into liquidity, efficiency, and profitability.",
          "- Performance Ratios: Net Profit margin, Return on Assets (ROA), Return on Equity (ROE), Return on Capital Employed (ROCE), Gross margin ratio.",
          "- Solvency Ratios: Current ratio = Current assets / Current liabilities, Leverage / Gearing, Operating cash flow / Interest paid, Operating cash flow / Operating profit.",
          "- Investor Ratios: Dividend yield, P/E ratio, Earnings per share (EPS), Dividend payout ratio."]),

        # Page 32
        ("The benefits of an annual report",
         ["The benefits of an annual report: Contains operational performance, financial performance, strategic direction.",
          "Financial components: Management discussion & analysis (MD&A), Financial statements, Notes to financial statements.",
          "Non-financial components: Messages from the Chair and CEO, Corporate profile, Risk and control processes."]),

        # Page 33
        ("Contents of an annual report",
         ["Contents of an annual report always include 9 key sections:",
          "01. Letters to the shareholders",
          "02. Business description",
          "03. Management's Discussion and Analysis (MD&A)",
          "04. Reporting on internal controls",
          "05. Audit report",
          "06. Balance sheet, Income Statement, Statement of Cash Flows",
          "07. Notes to the financial statements",
          "08. Earnings per share",
          "09. Listing of directors of the company"]),

        # Page 34
        ("Management discussion and analysis",
         ["Management Discussion and Analysis (MD&A):",
          "Provides information regarding past performance and future strategic direction:",
          "- Acts as a sort of variance analysis",
          "- Explains company performance",
          "- Lists future actions to be taken",
          "- Identifies key risks facing the organization"]),

        # Page 35
        ("Thank you",
         ["Thank you",
          "pwc.com/jm",
          "Copyright 2020 PricewaterhouseCoopers. All rights reserved. PwC refers to the Jamaica member firm."])
    ]

    for page_num, (title, paras) in enumerate(pages_data, start=1):
        page = doc.new_page(width=792, height=612) # Landscape orientation like presentation slides
        # Slide Header Banner
        header_rect = pymupdf.Rect(40, 25, 752, 60)
        page.draw_rect(header_rect, color=(0.85, 0.2, 0.15), fill=(0.85, 0.2, 0.15))
        page.insert_text((50, 48), f"PwC — {title}", fontsize=15, color=(1, 1, 1), fontname="helv")

        # Slide Content
        y = 90
        for para in paras:
            text_lines = [para[i:i+95] for i in range(0, len(para), 95)]
            for line in text_lines:
                page.insert_text((50, y), line, fontsize=11, color=(0.15, 0.15, 0.15), fontname="helv")
                y += 18
            y += 8

        # Footer
        footer_text = f"PwC | Basic Understanding of a Company's Financial Statements (Sept 2020) — Page {page_num} of 35"
        page.insert_text((50, 585), footer_text, fontsize=9, color=(0.45, 0.45, 0.45), fontname="helv")

    doc.save(str(pdf_path))
    doc.close()
    print(f"Generated 35-page PDF successfully at: {pdf_path}")
    return str(pdf_path)

if __name__ == "__main__":
    generate_pwc_pdf()
