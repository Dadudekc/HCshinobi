class TrainingSystem:
    def __init__(self) -> None:
        self.active_training = {}

    def get_training_status(self, user_id: int):
        return self.active_training.get(str(user_id))

    def get_training_status_embed(self, user_id: int):
        return None
