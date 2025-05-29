import pymysql
import pandas as pd

def get_connection():
    return pymysql.connect(
        host='118.33.79.86',
        port=3306,
        user='bluefin',
        password='gksxn20044!',
        db='scon',
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )

def load_all(sql: str, params: tuple = ()) -> list[dict]:
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.fetchall()
    finally:
        conn.close()

def load_df(sql: str, params: tuple = ()) -> pd.DataFrame:
    rows = load_all(sql, params)
    return pd.DataFrame(rows) if rows else pd.DataFrame()

def load_price(symbol: str, from_dt: str, to_dt: str = None, interval: int=60, limit: int = None) -> pd.DataFrame:
    if not from_dt:
        raise ValueError("from_dt is required for DB query.")

    to_dt = to_dt or pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")

    sql = """
        SELECT trade_date, open, high, low, close, volume
        FROM asset_price
        WHERE asset_id = %s 
        AND trade_date >= %s 
        AND trade_date < %s
        ORDER BY trade_date ASC
    """
    df = load_df(sql, (symbol, from_dt, to_dt))
    if df.empty:
        return df

    df['trade_date'] = pd.to_datetime(df['trade_date'])
    df.set_index('trade_date', inplace=True)
    df = df.resample(f"{interval}min").agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna()

    df = df.reset_index()
    print(df)
    # 컬럼명 강제 재정의 (예방용)
    df = df[['trade_date', 'open', 'high', 'low', 'close', 'volume']]
    df.columns = ['Date', 'open', 'high', 'low', 'close', 'volume']

    if limit:
        df = df.tail(limit)
    
    return df

#df = load_price('KTB3F', '2025-05-01', interval=60)
#print(df.head())