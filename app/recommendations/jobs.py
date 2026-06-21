from app.db.firestore_refs import recommendation_job_doc


class RecommendationJobRepository:
    def create(self, uid: str, job_id: str, data: dict) -> None:
        recommendation_job_doc(uid, job_id).set(data)

    def get(self, uid: str, job_id: str) -> dict | None:
        snapshot = recommendation_job_doc(uid, job_id).get()
        if not snapshot.exists:
            return None
        return snapshot.to_dict()

    def update(self, uid: str, job_id: str, data: dict) -> dict | None:
        ref = recommendation_job_doc(uid, job_id)
        if not ref.get().exists:
            return None
        ref.update(data)
        return ref.get().to_dict()
