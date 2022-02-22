class TableNotFoundException(Exception):
    def __init__(self, *args: object) -> None:
        self.message = "Couldn't get table information."
        self.code = 404
        super().__init__(*args)

    def __str__(self) -> str:
        return f"code: {self.code}, message: {self.message}"
