class Greeter:
    def __init__(self, name: str):
        self.name = name
    
    def greet(self) -> None:
        print(f"Hello, {self.name}!")

if __name__ == "__main__":
    greeter = Greeter("World")
    greeter.greet() 