export const timeOfDayGreeting = (hour = new Date().getHours()): string => {
  if (hour < 12) return 'Namaste! Good morning';
  if (hour < 18) return 'Namaste! Good afternoon';
  return 'Namaste! Good evening';
};

export const farewellGreeting = 'Bye! See you tomorrow';
