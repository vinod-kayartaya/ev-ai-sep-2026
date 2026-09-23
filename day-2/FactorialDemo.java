import java.util.Scanner;

public class FactorialDemo {
    public static void main(String[] args) {
        Scanner scanner = new Scanner(System.in);
        System.out.print("Enter a positive integer: ");
        int number = scanner.nextInt();
        long factorial = 1;

        for (int i = 1; i <= number; i++) {
            factorial *= i;
        }

        System.out.printf("Factorial of %d = %d", number, factorial);
        scanner.close();
    }
}