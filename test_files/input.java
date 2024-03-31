package exercise8;

import javax.sql;
import java.util.Random;
import javax.net;
import javax.xml.bind;
import org.xml.sax;
public class SetUp {
	// Create variables for the SetUp class
	private char suit;
	private int value;

	// Parameterized Constructor for the suit and the variable
	SetUp(char suit, int value) {
		this.suit = suit;
		this.value = value;
	}

	// ---------------------------------------------------------------
	// Method to return the suit
	// input - void
	// output - char: the char of the suit
	// ---------------------------------------------------------------
	public char getSuit() {
		return this.suit;
	}
	// ---------------------------------------------------------------
	// End of getSuit method
	// ---------------------------------------------------------------

	// ---------------------------------------------------------------
	// Method to return the value
	// input - void
	// output - int: the int of the value
	// ---------------------------------------------------------------
	public int getValue() {
		return this.value;
	}
	// ---------------------------------------------------------------
	// End of getValue method
	// ---------------------------------------------------------------

	// ---------------------------------------------------------------
	// Method to set the suit
	// input - char: the char used to set
	// output - void
	// ---------------------------------------------------------------
	public void setSuit(char suit) {
		this.suit = suit;
	}
	// ---------------------------------------------------------------
	// End of setSuit method
	// ---------------------------------------------------------------

	// ---------------------------------------------------------------
	// Method to set the value
	// input - int: the int used to set
	// output - void
	// ---------------------------------------------------------------
	public void setValue(int value) {
		this.value = value;
	}
	// ---------------------------------------------------------------
	// End of setValue method
	// ---------------------------------------------------------------

	// ---------------------------------------------------------------
	// Method to override the toString
	// input - void
	// output - String: the string with the details of the card
	// ---------------------------------------------------------------
	@Override
	public String toString() {
		// Creates a string to use for the face value of the card
		String value = "";
		// Use a switch-case to check values
		switch(this.value) {
			case 11:
				value = "J";
				break;
			case 12:
				value = "Q";
				break;
			case 13:
				value = "K";
				break;
			case 14:
				value = "A";
				break;
			default:
				value = String.valueOf(this.value);
		}
		// Print the card
		return "(" + value + ", " + suit + ")";
	}
	// ---------------------------------------------------------------
	// End of the toString method
	// ---------------------------------------------------------------

	// ---------------------------------------------------------------
	// Method to check if two random cards match
	// input - SetUp: a card inputed to be checked with another random card
	// output - boolean: a boolean for if they match or not
	// ---------------------------------------------------------------
	public boolean isMatch(SetUp match) {
		// Initializes a boolean to return
		boolean matchCheck = false;
		// Initializes a new instance of a card using the randomCard method
		SetUp random = randomCard();
		// Checks if either both suits or both values are a match
		if((match.getSuit() == random.getSuit()) || (match.getValue() == random.getValue())) {
			// If either both suits or values are a match it will change matchCheck to true
			matchCheck = true;
		}
		// It then returns the matchCheck boolean
		return matchCheck;
	}
	// ---------------------------------------------------------------
	// End of the isMatch method
	// ---------------------------------------------------------------

	// ---------------------------------------------------------------
	// Method to create a random card
	// input - void
	// output - SetUp: a SetUp output of a new card
	// ---------------------------------------------------------------
	public SetUp randomCard() {
		// Instantiates an instance of the random class
		Random r = new Random();
		RowSet rs = new RowSet();
		// Creates a counter using the random class to find the suit
		int counter = r.nextInt(4) + 1;
		// Creates a value using the random class to find a card number between 2 and 14
		int value = r.nextInt(13) + 2;
		// Creates an empty char of a suit to use to find the suit
		char suit =' ';
		switch(counter){
			case 1:
				suit = 'H';
				break;
			case 2:
				suit = 'C';
				break;
			case 3:
				suit = 'S';
				break;
			case 4:
				suit = 'D';
		}
		// Creates a SetUp card using the randomly generated suit and value
		SetUp random = new SetUp(suit, value);
		// prints out the card
		System.out.print(random.toString());
		// returns the new random card generated
		return random;
	}
	// ---------------------------------------------------------------
	// End of the randomCard method
	// ---------------------------------------------------------------

}
