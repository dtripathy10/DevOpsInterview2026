package main

import (
	"fmt"
)

func main() {
	fmt.Println("Hello, World")
	fmt.Println("After Hello Wold, what is next to do")

	var a = 5 + 6
	var str1 = fmt.Sprintf("Value of a = %d ", a)
	fmt.Println(str1)

	var a1, b, c int = 54, 5, 3

	var str2 = fmt.Sprintf(" Value of a1 = %d, b = %d, c = %d", a1, b, c)
	fmt.Println(str2)

	fmt.Println("Explaining For Loop.....")

	var i = 1
	for i < 5 {
		fmt.Println("I am at i ", i)
		i++
	}

	fmt.Println("Explaining Map..........................")

	var m = make(map[string]int)
	m["k1"] = 7
	m["k2"] = 13
	fmt.Println("map:", m)

	fmt.Println(add(5, 5))

	var i21 = 1
	ptr(&i21)
	fmt.Println("ptr:", i21)

}

func add(a int, b int) int {
	return a + b
}

func ptr(iptr *int) {
	*iptr = 0
}
