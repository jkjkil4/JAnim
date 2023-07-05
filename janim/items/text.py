from janim.items.item import Item

class Text(Item):
    def __init__(self, text) -> None:
        super().__init__()
        self.text = text
    
    def get_comment(self) -> str:
        if len(self.text) > 20:
            return self.text[:20] + ' ...'
        return self.text
