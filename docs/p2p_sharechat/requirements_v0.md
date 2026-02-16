  
Sharechat- Sweta’s Team: Finance  
Procure to Pay(P2P) ops:

Task list: P2P operations

| P2P Operations Issues | Category | Details | System of Truth |
| :---- | :---- | :---- | :---- |
| Payment Status Queries | Payments | Vendors and internal employees send queries asking about payment status. Sometimes they have invoice number, sometimes just vendor name. | Netsuite |
| Document Format Conversion-Bank upload file formatting | Documents | Payment files must be formatted in specific bank upload format |  |
| Invoice Data Entry. OCR solution with SAP attempted but failed (why?) | Invoice | Invoices received via email must be manually entered into NetSuite.  | Netsuite, email |
| Employee Reimbursements( where it originates from).  | Reimbursements | Manual processing and verification of employee reimbursements required. Sharing a report with AP team |  |
| Unable to generate statistics on invoices processed per month, payments made per month, and other efficiency metrics | P2P Metrics | Need a report to track this. | Netsuite |
| Key Vendor Priority Responses | Vendor management | Key vendors (Google, Agora, Tencent) need immediate holding replies when asking about payment status |  |
|  |  |  |  |
| Credit Card Invoice Reconciliation | Credit Card Recon | Difficulty in locating credit card invoices and performing reconciliation manually |  |
| Manual Bank Entries | Bank entry | Bank entries are created manually without automation |  |

| Accrual Tracking | Accruals | Need to track accruals that may have been missed. They occur monthly but there’s risk of missing accruals. |  |
| :---- | :---- | :---- | :---- |
| Manual Vendor Creation | Vendor Creation | All vendor creation must be done manually in the system |  |
| Vendor payment on time | Payments | Reminders to approvers on slack and email for approving transactions with priority list | NETSUITE |
| Kyc check on vendors( which tool being used as of now, how they upload vendor documents, how vendor onboarding happens), where is the agreement? | Vendor management | KYC check on onboarding documents |  |
| Payment delay emails | Vendor management | Sharing details with MSME and foreign payments on monthly basis | Netsuite |
| Vendor onboarding status | Vendor management | All documents received check and auto status report | Spotdraft , Netsuite |

#### 

|  |  |
| ----- | ----- |
|  |  |
|  |  |

 

#### **2\. Agents to Build Using the Agent Development Kit (ADK)**

These tasks involve more complex workflows, custom logic, and integration with external systems like NetSuite. The ADK provides the flexibility needed to build robust and scalable solutions for these scenarios.

| Task | Rationale  |
| ----- | ----- |
| Document format conversion | An ADK agent can be built with a custom tool to handle specific and complex document transformations from one format to another. |
| Payment file formatting | This requires a custom tool within an ADK agent to generate files in a specific bank upload format, which often has a rigid structure and requires data transformation. |
| Invoice data entry into NetSuite | This is a multi-step process that can be orchestrated by an ADK agent. The agent can use an OCR tool to extract data from invoices and then use a custom NetSuite tool to create the invoice record. Given your past experience with OCR, the ADK would also allow for a human-in-the-loop for verification. |
| Employee reimbursements | This is a complex workflow that an ADK agent can manage from end to end, including policy checks, approval routing, and integration with NetSuite and payment systems. |
| P2P metrics and reporting | An ADK agent can be developed to connect to NetSuite, extract data, perform complex calculations, and generate customized reports on P2P efficiency metrics. |
| Tracking accruals | This requires an ADK agent with custom logic to analyze financial data from NetSuite, apply accounting rules to identify missed accruals, and flag them for review. |
| Manual Vendor Creation | An ADK agent can streamline this by guiding a user through the vendor creation process and then using a NetSuite tool to create the vendor, ensuring all required fields are filled correctly. |
| Manual bank entries | An ADK agent can automate this by parsing bank statements and using a NetSuite tool to create the corresponding entries, reducing manual effort and errors. |
| Credit card invoice reconciliation | This complex reconciliation task is a good fit for an ADK agent, which can be programmed to fetch data from multiple sources, match transactions, and flag discrepancies. |
| Manual employee reimbursement verification | An ADK agent can automate the verification process by using custom tools to check receipts and claims against company policies, then route them for approval. |

 

| Task | Rationale |
| ----- | ----- |
| Querying payment status | agent can be trained to understand user queries about payment status and retrieve information from a connected data source like Netsuite |

### **ADK and Authentication**

Regarding your question about how the ADK handles authentication for connected tools:

The Agent Development Kit (ADK) does not automatically get authentication from Google Workspace or Gemini. Instead, the developer building the agent is responsible for implementing the authentication mechanism for each connected tool.

* For Google Workspace apps, you would typically use OAuth 2.0, where the user grants the agent permission to access their data.  
* For other tools like NetSuite, you would use the authentication method provided by their API, such as Token-Based Authentication (TBA). You would write code within your custom tool to handle this authentication, and you can use a secure service like Google Cloud Secret Manager to store the necessary API keys and tokens.

### **Connecting Gemini Enterprise with NetSuite**

Here is the general process for connecting Gemini Enterprise to NetSuite, which would be done as part of building an agent with the ADK:

1. Enable API Access in NetSuite: A NetSuite administrator will need to enable API access and create an "Integration" record.  
2. Set Up Authentication: It is highly recommended to use NetSuite's Token-Based Authentication (TBA). This will generate a set of secure credentials (consumer key/secret and token ID/secret) for your agent to use.  
3. Develop a Custom NetSuite Tool: Using the ADK, you will write a custom tool in Python that can make API calls to NetSuite. This tool will include the logic to authenticate with NetSuite using the credentials from the previous step. The tool will have functions for the actions you want to automate (e.g., create\_invoice, get\_payment\_status).  
4. Securely Store Credentials: The NetSuite credentials should not be hardcoded in your agent's code. Instead, store them securely in a service like Google Cloud Secret Manager. Your custom tool will then be programmed to retrieve these credentials at runtime.  
5. Build the Agent: With the custom NetSuite tool in place, you can build your agent to use the tool's functions to automate your P2P workflows.

Execution Plan:

We use of Google ADK agents that perform these task.

1. Find out how many agents we need  
2. What tools each agents need  
3. What workflow each agents require to achieve the work. O theta is their work?  
4. We create netsuite and spotdraft mock server using apis and auth so that these google adk agents gets connected to them   
5. A separate connector page for these agents. Like netsutie and spotdraft with auth mimicking the real so that user can use mock auth to test and then switch to real later.  
6. We run the test using ADK web ui. 

