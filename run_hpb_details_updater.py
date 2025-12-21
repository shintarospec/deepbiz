import time
from sqlalchemy import or_, and_

# app.pyから必要なものをインポート
from app import app, db, get_hpb_details
from models import Salon, ReviewSummary

def update_hpb_details_batch():
    """
    HPBのURLが登録済みで、まだ詳細情報（評価・口コミ数）が
    未取得のサロンを対象に、情報を取得してDBを更新するバッチ処理。
    """
    with app.app_context():
        print("--- HPB詳細情報の更新バッチを開始します ---")

        # --- 更新対象のサロンを取得 ---
        # 1. hotpepper_urlが存在する
        # 2. Hot PepperのReviewSummaryが存在しない、OR 存在するがratingがNULL (前回失敗した)
        
        # SQLAlchemyのouterjoinを使って、ReviewSummaryが存在しないサロンも対象に含める
        target_salons = db.session.query(Salon).outerjoin(
            ReviewSummary, 
            and_(
                Salon.id == ReviewSummary.salon_id,
                ReviewSummary.source_name == 'Hot Pepper'
            )
        ).filter(
            Salon.hotpepper_url.isnot(None),
            or_(
                ReviewSummary.id.is_(None),
                ReviewSummary.rating.is_(None)
            )
        ).all()

        total_targets = len(target_salons)
        print(f"-> 更新対象のサロンが {total_targets} 件見つかりました。")

        if total_targets == 0:
            print("--- 全てのサロンの情報が取得済みです。バッチを終了します ---")
            return

        # --- 1件ずつ処理を実行 ---
        for i, salon in enumerate(target_salons):
            print(f"\n({i+1}/{total_targets}) {salon.name_hpb or salon.name} の情報を処理中...")
            print(f"  URL: {salon.hotpepper_url}")

            if not salon.hotpepper_url:
                print("  -> URLがありません。スキップします。")
                continue

            # app.pyで完成させたヘルパー関数を実行
            details = get_hpb_details(salon.hotpepper_url)

            if details:
                # --- 取得成功：データベースを更新 ---
                try:
                    # 住所が空の場合のみ、取得した住所で更新
                    if not salon.address and details.get('address'):
                        salon.address = details.get('address')
                        print(f"  -> 住所を更新しました: {salon.address}")

                    # 評価と口コミ件数をReviewSummaryテーブルに保存/更新
                    if details.get('rating') is not None or details.get('review_count') is not None:
                        hpb_summary = ReviewSummary.query.filter_by(
                            salon_id=salon.id, 
                            source_name='Hot Pepper'
                        ).first()

                        if not hpb_summary:
                            hpb_summary = ReviewSummary(salon_id=salon.id, source_name='Hot Pepper')
                            db.session.add(hpb_summary)
                            print("  -> 新しいReviewSummaryレコードを作成しました。")
                        
                        hpb_summary.rating = details.get('rating')
                        hpb_summary.count = details.get('review_count')
                        print(f"  -> 評価: {hpb_summary.rating}, 口コミ数: {hpb_summary.count} で更新します。")

                    db.session.commit()
                    print("  -> [成功] データベースの更新が完了しました。")

                except Exception as e:
                    db.session.rollback()
                    print(f"  -> [エラー] DB更新中にエラーが発生: {e}")
            else:
                # --- 取得失敗 ---
                print("  -> [失敗] 詳細情報の取得に失敗しました。")

            # サーバーに負荷をかけすぎないよう、1秒待機
            time.sleep(1)

        print("\n--- 全ての処理が完了しました。バッチを終了します ---")

if __name__ == '__main__':
    update_hpb_details_batch()
