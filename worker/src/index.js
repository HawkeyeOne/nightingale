import { EmailMessage } from "cloudflare:email";
import { createMimeMessage } from "mimetext/browser";

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type",
};

export default {
  async fetch(request, env) {
    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: CORS });
    }

    if (request.method !== "POST") {
      return new Response("Method Not Allowed", { status: 405 });
    }

    let body;
    try {
      body = await request.json();
    } catch {
      return Response.json({ error: "Invalid JSON" }, { status: 400, headers: CORS });
    }

    const { name, email, phone, course, message } = body;

    if (!name || !email || !phone || !course) {
      return Response.json({ error: "Missing required fields" }, { status: 400, headers: CORS });
    }

    const msg = createMimeMessage();
    msg.setSender({ name: "Nightingale RN Academy Website", addr: "noreply@nightingalernacademy.com" });
    msg.setRecipient("nightingale.rn.academy@gmail.com");
    msg.setSubject(`Course Inquiry: ${course}`);
    msg.addMessage({
      contentType: "text/html",
      data: `
        <h2>New Course Inquiry</h2>
        <table style="border-collapse:collapse;font-family:sans-serif;font-size:15px;">
          <tr><td style="padding:6px 16px 6px 0;font-weight:bold;">Course</td><td>${course}</td></tr>
          <tr><td style="padding:6px 16px 6px 0;font-weight:bold;">Name</td><td>${name}</td></tr>
          <tr><td style="padding:6px 16px 6px 0;font-weight:bold;">Email</td><td><a href="mailto:${email}">${email}</a></td></tr>
          <tr><td style="padding:6px 16px 6px 0;font-weight:bold;">Phone</td><td><a href="tel:${phone}">${phone}</a></td></tr>
          ${message ? `<tr><td style="padding:6px 16px 6px 0;font-weight:bold;vertical-align:top;">Message</td><td>${message}</td></tr>` : ""}
        </table>
      `,
    });

    try {
      const emailMessage = new EmailMessage(
        "noreply@nightingalernacademy.com",
        "nightingale.rn.academy@gmail.com",
        msg.asRaw()
      );
      await env.SEND_EMAIL.send(emailMessage);
    } catch (err) {
      console.error("Email send failed:", err);
      return Response.json({ error: "Failed to send email" }, { status: 500, headers: CORS });
    }

    return Response.json({ success: true }, { headers: CORS });
  },
};
