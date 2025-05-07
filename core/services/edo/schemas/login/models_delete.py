from datetime import datetime

from pydantic import BaseModel


class Profile(BaseModel):
    id: int
    date: datetime
    fio: str
    inn: str
    chat_id: str
    thumbprint: str
    edo_provider: int
    to_delete: bool = False


class DeleteProfiles(BaseModel):
    profiles: list[Profile]

    def reverse_mark(self, inn: str):
        for profile in self.profiles:
            if profile.inn == inn:
                profile.to_delete = True if not profile.to_delete else False
        return self

    def profiles_to_delete(self) -> list[Profile]:
        return [profile for profile in self.profiles if profile.to_delete]
