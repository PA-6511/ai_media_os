"""Durable SQLite outbox shared by every store URL writer."""
import sqlite3

def install(db):
    db.executescript("""
    CREATE TABLE IF NOT EXISTS cover_registration_jobs (
      ebook_item_id TEXT PRIMARY KEY REFERENCES ebook_items(id) ON DELETE CASCADE,
      revision INTEGER NOT NULL DEFAULT 1,
      attempts INTEGER NOT NULL DEFAULT 0,
      status TEXT NOT NULL DEFAULT 'PENDING',
      reason TEXT NOT NULL DEFAULT 'URL_REGISTERED',
      next_attempt_at INTEGER NOT NULL DEFAULT 0,
      updated_at INTEGER NOT NULL DEFAULT 0
    );
    CREATE TRIGGER IF NOT EXISTS cover_url_insert AFTER INSERT ON store_offers
    WHEN coalesce(NEW.product_url,NEW.affiliate_url,'') <> ''
    BEGIN
      INSERT INTO cover_registration_jobs(ebook_item_id,updated_at)
      VALUES(NEW.ebook_item_id,strftime('%s','now'))
      ON CONFLICT(ebook_item_id) DO UPDATE SET revision=revision+1,
      attempts=0,status='PENDING',reason='URL_REGISTERED',next_attempt_at=0,
      updated_at=strftime('%s','now');
    END;
    CREATE TRIGGER IF NOT EXISTS cover_url_update
    AFTER UPDATE OF product_url,affiliate_url,store_item_id ON store_offers
    WHEN NEW.product_url IS NOT OLD.product_url
      OR NEW.affiliate_url IS NOT OLD.affiliate_url
      OR NEW.store_item_id IS NOT OLD.store_item_id
    BEGIN
      INSERT INTO cover_registration_jobs(ebook_item_id,updated_at)
      VALUES(NEW.ebook_item_id,strftime('%s','now'))
      ON CONFLICT(ebook_item_id) DO UPDATE SET revision=revision+1,
      attempts=0,status='PENDING',reason='URL_REGISTERED',next_attempt_at=0,
      updated_at=strftime('%s','now');
    END;
    """)

if __name__=='__main__':
    from app.db.config import DATABASE_URL
    assert DATABASE_URL.startswith('sqlite:///')
    with sqlite3.connect(DATABASE_URL.removeprefix('sqlite:///')) as db:
        install(db)
    print('COVER_REGISTRATION_QUEUE_INSTALLED')
