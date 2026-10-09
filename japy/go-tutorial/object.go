package main

import (
	"fmt"
)

type Person struct {
	name string
	age  int
}

func createNewPerson(name string, age int) *Person {
	p := Person{
		name: name,
		age:  age,
	}
	return &p
}

func main() {
	fmt.Println("It is enough for now....")
	var p = createNewPerson("Deba", 36)
	fmt.Println(p)

}
