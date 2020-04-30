# Form Management Flask Application

## Main Features
- View available Zoom meetings that you can create a form for.
- Create multiple forms associated with a specific meeting.
- View how many people have successfully signed up for a meeting using a form and their signup details.
- Click to copy the form's public view for easy sharing.
- Toggle access to the form. If deactivated, external users can't access the form to register for a meeting.

## Key Architectural Choices

### Data Models
The app has `User`, `MeetingForm`, and `Registrant` objects. A user can have many forms, and a form can have many registrants.

### Zoom Integration
I successfully tried to use OAuth first, but then I figured that if a registrant access the public view of the form, when he/she submits (POST), the client will likely try to get a refresh token, but it won't do so for the Zoom account of the form's creator, but for the registrant's account. As such, I switched back to using JWT, which will allow registrants to submit changes to the creator's account without any further authentication, which is what we want.

JWT is simpler to implement, but then it requires users to manually provide credentials to the app. Currently, I'm saving credentials to the `User` object. Users can change API credentials, and they are only allowed to manage forms for meetings that are provided by the current API credentials. I figured that it would be reasonable to put this restriction in place.
### Features
While the UI can be a bit better, I did include some thoughtful features that are user-friendly in the context of this app:

- Meetings associated with the API credentials are grabbed and listed on the home page, and users can directly press a link to go to a pre-filled "meta-form" to create the viewable form that registrants will view.
- Each meeting form has its own page, where creators can view details of registrants that signed up with this form. The page also has a quick "click-to-copy" tool for easy sharing. Also, user can activate or deactivate the form, which will toggle its public status. I chose deactivation instead of deletion of forms because it is more friendly to handle in the DB.
- One can create multiple forms for one meeting. This ability can be helpful in the future if the app is extended to allow more form customization (right now the fields are static). It would be useful to tailor the form's appearance/content to different audiences, even if they are signing up for the same meeting. Of course, if a person tries to register for a meeting that he/she already registered for but through a different form, the app will throw an error.

## Potential Extensions
- More eye-catching UI
- Build out the ability to customize form content/layout (e.g a Google Forms-like feature).
