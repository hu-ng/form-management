function copyLink() {
  console.log("Hello")
  /* Get the text field */
  let copyText = document.getElementById("meeting-link");

  /* Select the text field */
  copyText.select();

  /* Copy the text inside the text field */
  document.execCommand("copy");

  /* Alert the copied text */
  alert("Copied the text: " + copyText.value);
}