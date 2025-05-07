import enum


class Roles(enum.Enum):
    USER = "Клиент"
    ADMIN = "Админ"
    TEHPOD = "Техпод"
    SAMAN_PROVIDER = "Представитель Саман"
    PREMIER_PROVIDER = "Представитель Премьер"
    ROSSICH_PROVIDER = "Представитель Россич"
    ALKOTORG_PROVIDER = "Представитель Алкоторг"


def providers() -> list[str]:
    return [
        Roles.SAMAN_PROVIDER,
        Roles.PREMIER_PROVIDER,
        Roles.ROSSICH_PROVIDER,
        Roles.ALKOTORG_PROVIDER,
    ]
