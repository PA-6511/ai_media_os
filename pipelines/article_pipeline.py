from typing import Dict


class ArticlePipeline:
    def __init__(self, logger):
        self.logger = logger

    def run(self, task: Dict) -> Dict:
        target = task.get("target", "")
        self.logger.info("[Pipeline] 記事生成を開始: %s", target)

        result = {
            "status": "success",
            "action": task.get("action"),
            "target": target,
            "message": f"記事を生成しました: {target}",
        }

        self.logger.info("[Pipeline] 処理完了: %s", result["message"])
        return result
