import logging
import pandas as pd
import numpy as np
from datetime import date
from typing import Optional, Tuple
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters


class moneyMate:

    # this helps to know if there are any errors
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )

    def __init__(self):
        # we are using a pandas df to store all the data
        self.df = pd.DataFrame(
            {'Date': [],
             'Product': [],
             'Amount': [],
             'Category': []
             })

        self.budgets = {

        }

    async def clear_df(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.df = pd.DataFrame(
            {'Date': [],
             'Product': [],
             'Amount': [],
             'Category': []
             })

    async def random_spents(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Parameters for generating random data
        categories = ["groceries", "so", "essentials",
                      "clothes", "entertainment", "transport", "going out"]
        start_date = "2023-01-01"
        end_date = "2025-12-31"
        num_records = 1000

        # Generate random data
        np.random.seed(42)  # For reproducibility
        random_dates = pd.to_datetime(np.random.choice(
            pd.date_range(start_date, end_date), size=num_records))
        random_categories = np.random.choice(categories, size=num_records)
        random_amounts = np.random.randint(100, 80001, size=num_records)

        # Create DataFrame
        df = pd.DataFrame({
            "Date": random_dates,
            "Product": "Product",
            "Amount": random_amounts,
            "Category": random_categories,
        })

        # Sorting by date for better usability
        self.df = df.sort_values(by="Date").reset_index(drop=True)

        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text="Random spents generated")

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # object update contains information about the message
        # object context contains information about the library
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text="Hi Im Spendings Master, how can i help you?")

    async def add_spending(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        spending = context.args

        if (len(spending) == 3):
            spending = [i.replace(",", "") for i in spending]
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id,
                                           text=f"🚫 Invalid format 🚫\nTry this format: /add product, spent, category")
            return

        date = update.message.date.isoformat(
            sep=" ").split(" ")[0]

        newRow = pd.DataFrame({'Date': [pd.to_datetime(date)],
                               'Product': [spending[0]],
                               'Amount': [int(spending[1])],
                               'Category': [spending[2]]
                               })

        remaining = self.budgets[spending[2]] - int(spending[1])

        self.df = pd.concat([self.df, newRow], ignore_index=True)
        self.budgets[spending[2]] = remaining

        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text=f"💸  Spent  💸\n\n \t\t📅  {date}\n \t\t📦  {spending[0].capitalize()}\n \t\t💰  ${int(spending[1])}\n \t\t📝  {spending[2].capitalize()}\n\n ✅  Added successfully  ✅")

        if (remaining <= 0):
            await context.bot.send_message(chat_id=update.effective_chat.id,
                                           text="🚫 You went over the budget 🚫")
        return

    async def unknown(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text="Sorry, I didn't understand that command.")
        return

    async def balance(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Calculate balance for given time period.
        Supports querying by: month, year, specific date, or month-year combination.
        """
        months = {
            str(i): month for i, month in enumerate([
                "January", "February", "March", "April", "May", "June",
                "July", "August", "September", "October", "November", "December"
            ], 1)
        }

        def parse_date_args(args) -> Tuple[Optional[int], Optional[int], Optional[int]]:
            """Parse command arguments into day, month, year."""
            today = date.today()
            if not args:
                return None, today.month, today.year

            # Convert all args to integers
            try:
                numbers = [int(arg) for arg in context.args]
            except ValueError:
                raise ValueError("All arguments must be numbers")

            if len(numbers) == 1:
                num = numbers[0]
                if 1 <= num <= 12:
                    return None, num, today.year
                elif 2020 <= num <= 2025:
                    return None, None, num
                else:
                    raise ValueError(
                        "Single argument must be month (1-12) or year (2020-2025)")

            elif len(numbers) == 2:
                month, year = numbers
                if 1 <= month <= 12 and 2023 <= year <= 2025:
                    return None, month, year
                else:
                    raise ValueError("Format: month (1-12) year (2023-2025)")

            elif len(numbers) == 3:
                day, month, year = numbers
                if 1 <= day <= 31 and 1 <= month <= 12 and 2023 <= year <= 2025:
                    return day, month, year
                else:
                    raise ValueError(
                        "Format: day (1-31) month (1-12) year (2023-2025)")

            raise ValueError("Invalid number of arguments")

        try:
            day, month, year = parse_date_args(context.args)

            mask = self.df['Date'].dt.year == year
            if month:
                mask &= self.df['Date'].dt.month == month
            if day:
                mask &= self.df['Date'].dt.day == day

            res = self.df[mask]

            # format the response message
            if day:
                date_str = f"{day}-{month}-{year}"
            elif month:
                date_str = f"{months[str(month)]} {year}"
            else:
                date_str = str(year)

            command = update.message.text.split()[0]

            if command == '/spent':
                await context.bot.send_message(chat_id=update.effective_chat.id,
                                               text=f"On {date_str} you spent on:\n{res.iloc[1::].to_string(index=False)}")
                return
            if command == '/total':
                await update.message.reply_text(f"You spent ${res['Amount'].sum():,.2f} in {date_str}")
                return

        except ValueError as e:
            await update.message.reply_text(str(e))
            return
        except Exception as e:
            await update.message.reply_text("An error occurred while calculating your balance.")
            return

    async def delete_spending(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if self.df.empty:
            await update.message.reply_text("No expenses to delete")
            return
        else:
            self.df = self.df.iloc[:-1]
        await update.message.reply_text("Last expense deleted")
        return

    async def cat_budget(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        '/budget [category] [budget]'

        message = context.args

        if (len(message) == 2 and (type(int(message[1])) == int) and (type(message[0]) == str)):
            category, budget = message

            self.budgets[category] = int(budget)

            await update.message.reply_text(f"Budget correctly allocated  📊\n\nFor this month you only can spent ${budget} in {category}")
        else:
            await update.message.reply_text("Format not valid for a budget, try /budget [category] [budget]")

    async def categories(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        categories = self.budgets.keys

        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"{categories.__str__}")
        return
