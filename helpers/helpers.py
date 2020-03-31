from models import Account, db


def update_user_accounts(accounts):
    for account in accounts:
        id = account["id"]
        account_in_db = Account.query.get(id)

        if account_in_db:
            account_in_db.currency = account["currency"]
            account_in_db.balance = account["balance"]
            account_in_db.available = account["available"]
            account_in_db.hold = account["hold"]
            db.session.add(account_in_db)

        else:
            currency = account["currency"]
            balance = account["balance"]
            available = account["available"]
            hold = account["hold"]

            account = Account(id=id, currency=currency,
                              balance=balance, available=available, hold=hold, user_id=user_id)

            db.session.add(account)

    db.session.commit()
