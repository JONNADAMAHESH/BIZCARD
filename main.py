# =====================================================   /   /   Import library   /   /   ================================================= #

# [Scanning library]
import easyocr # (Optical Character Recognition)
import numpy as np
from PIL import Image, ImageDraw
import re

# [Data frame libraries]
import pandas as pd

# [Database library]
import sqlalchemy
import pymysql
from sqlalchemy import create_engine

# [Dashboard library]
import streamlit as st

# ===================================================   /   /   Dash Board   /   /   ======================================================== #

# Configuring Streamlit GUI
st.set_page_config(layout='wide')

# Title
st.title(':blue[Business Card Data Extraction]')

# Tabs
tab1, tab2 = st.tabs(["Data Extraction zone", "Data modification zone"])

# ==========================================   /   /   Data Extraction and upload zone   /   /   ============================================== #

with tab1:
    st.subheader(':red[Data Extraction]')

    # Image file uploader
    import_image = st.file_uploader('**Select a business card (Image file)**', type=['png', 'jpg', 'jpeg'], accept_multiple_files=False)

    # Note
    st.markdown('''File extension support: **PNG, JPG, JPEG**, File size limit: **2 MB**, Image dimension limit: **1500 pixels**, Language: **English**.''')

    if import_image is not None:
        try:
            # Create the reader object with desired languages
            reader = easyocr.Reader(['en'], gpu=False)

            # Read the image file as a PIL Image object
            image = Image.open(import_image)
            image_array = np.array(image)
            text_read = reader.readtext(image_array)

            result = [text[1] for text in text_read]

            # Define a function to draw the box on the image
            def draw_boxes(image, text_read, color='yellow', width=2):
                image_with_boxes = image.copy()
                draw = ImageDraw.Draw(image_with_boxes)
                for bound in text_read:
                    p0, p1, p2, p3 = bound[0]
                    draw.line([*p0, *p1, *p2, *p3, *p0], fill=color, width=width)
                return image_with_boxes

            # Display the processed card with a yellow box
            col1, col2 = st.columns(2)
            with col1:
                result_image = draw_boxes(image, text_read)
                st.image(result_image, caption='Captured text')

            # Data processing and conversion into DataFrame
            data = {
                "Company_name": [],
                "Card_holder": [],
                "Designation": [],
                "Mobile_number": [],
                "Email": [],
                "Website": [],
                "Area": [],
                "City": [],
                "State": [],
                "Pin_code": [],
            }

            def get_data(res):
                city = ""
                for ind, i in enumerate(res):
                    if "www " in i.lower() or "www." in i.lower():
                        data["Website"].append(i)
                    elif "WWW" in i:
                        data["Website"].append(res[ind-1] + "." + res[ind])
                    elif "@" in i:
                        data["Email"].append(i)
                    elif "-" in i:
                        data["Mobile_number"].append(i)
                        if len(data["Mobile_number"]) == 2:
                            data["Mobile_number"] = " & ".join(data["Mobile_number"])
                    elif ind == len(res) - 1:
                        data["Company_name"].append(i)
                    elif ind == 0:
                        data["Card_holder"].append(i)
                    elif ind == 1:
                        data["Designation"].append(i)
                    if re.findall("^[0-9].+, [a-zA-Z]+", i):
                        data["Area"].append(i.split(",")[0])
                    elif re.findall("[0-9] [a-zA-Z]+", i):
                        data["Area"].append(i)
                    match1 = re.findall(".+St , ([a-zA-Z]+).+", i)
                    match2 = re.findall(".+St,, ([a-zA-Z]+).+", i)
                    match3 = re.findall("^[E].*", i)
                    if match1:
                        city = match1[0]
                    elif match2:
                        city = match2[0]
                    elif match3:
                        city = match3[0]
                    state_match = re.findall("[a-zA-Z]{9} +[0-9]", i)
                    if state_match:
                        data["State"].append(i[:9])
                    elif re.findall("^[0-9].+, ([a-zA-Z]+);", i):
                        data["State"].append(i.split()[-1])
                    if len(data["State"]) == 2:
                        data["State"].pop(0)
                    if len(i) >= 6 and i.isdigit():
                        data["Pin_code"].append(i)
                    elif re.findall("[a-zA-Z]{9} +[0-9]", i):
                        data["Pin_code"].append(i[10:])
                data["City"].append(city)

            get_data(result)
            data_df = pd.DataFrame(data)
            st.dataframe(data_df.T)

            # Data Upload to MySQL
            class SessionState:
                def __init__(self, **kwargs):
                    self.__dict__.update(kwargs)
            session_state = SessionState(data_uploaded=False)

            st.write('Click the :red[**Upload to MySQL DB**] button to upload the data')
            Upload = st.button('**Upload to MySQL DB**', key='upload_button')

            if Upload:
                session_state.data_uploaded = True

            if session_state.data_uploaded:
                try:
                    connect = pymysql.connect(
                        host="127.0.0.1",
                        user="root",
                        password="Mahesh2005",
                    )
                    mycursor = connect.cursor()
                    mycursor.execute("CREATE DATABASE IF NOT EXISTS bizcard_db")
                    mycursor.close()
                    connect.database = "bizcard_db"
                    engine = create_engine('mysql+pymysql://root:Mahesh2005@localhost/bizcard_db', echo=False)
                    data_df.to_sql('bizcardx_data', engine, if_exists='append', index=False, dtype={
                        "Company_name": sqlalchemy.types.VARCHAR(length=225),
                        "Card_holder": sqlalchemy.types.VARCHAR(length=225),
                        "Designation": sqlalchemy.types.VARCHAR(length=225),
                        "Mobile_number": sqlalchemy.types.String(length=50),
                        "Email": sqlalchemy.types.TEXT,
                        "Website": sqlalchemy.types.TEXT,
                        "Area": sqlalchemy.types.VARCHAR(length=225),
                        "City": sqlalchemy.types.VARCHAR(length=225),
                        "State": sqlalchemy.types.VARCHAR(length=225),
                        "Pin_code": sqlalchemy.types.String(length=10)
                    })
                    st.info('Data Successfully Uploaded')
                except Exception as e:
                    st.error(f"Error uploading data: {e}")
                finally:
                    connect.close()
                session_state.data_uploaded = False

        except Exception as e:
            st.error(f"Error processing the image: {e}")
    else:
        st.info('Click the Browse file button and upload an image')

# =================================================   /   /   Modification zone   /   /   ==================================================== #

with tab2:
    col1, col2 = st.columns(2)

    # ------------------------------   /   /   Edit option   /   /   -------------------------------------------- #

    with col1:
        st.subheader(':red[Edit option]')

        try:
            conn = pymysql.connect(
                host="127.0.0.1",
                user="root",
                password="Mahesh2005",
                database="bizcard_db"
            )

            cursor = conn.cursor()
            cursor.execute("SELECT card_holder FROM bizcardx_data")
            rows = cursor.fetchall()
            names = [row[0] for row in rows]

            cardholder_name = st.selectbox("**Select a Cardholder name to Edit the details**", names, key='cardholder_name')
            cursor.execute("SELECT Company_name, Card_holder, Designation, Mobile_number, Email, Website, Area, City, State, Pin_code FROM bizcardx_data WHERE card_holder=%s", (cardholder_name,))
            col_data = cursor.fetchone()

            Company_name = st.text_input("Company name", col_data[0])
            Card_holder = st.text_input("Cardholder", col_data[1])
            Designation = st.text_input("Designation", col_data[2])
            Mobile_number = st.text_input("Mobile number", col_data[3])
            Email = st.text_input("Email", col_data[4])
            Website = st.text_input("Website", col_data[5])
            Area = st.text_input("Area", col_data[6])
            City = st.text_input("City", col_data[7])
            State = st.text_input("State", col_data[8])
            Pin_code = st.text_input("Pincode", col_data[9])

            session_state = SessionState(data_update=False)

            st.write('Click the :red[**Update**] button to update the modified data')
            update = st.button('**Update**', key='update')

            if update:
                session_state.data_update = True

            if session_state.data_update:
                try:
                    cursor.execute(
                        "UPDATE bizcardx_data SET Company_name = %s, Designation = %s, Mobile_number = %s, Email = %s, "
                        "Website = %s, Area = %s, City = %s, State = %s, Pin_code = %s WHERE Card_holder = %s",
                        (Company_name, Designation, Mobile_number, Email, Website, Area, City, State, Pin_code, Card_holder)
                    )
                    conn.commit()
                    st.info('Data updated successfully')
                except Exception as e:
                    st.error(f"Error updating data: {e}")
                finally:
                    cursor.close()
                    conn.close()
                session_state.data_update = False

        except Exception as e:
            st.error(f"Error connecting to the database: {e}")

    # ------------------------------   /   /   Delete option   /   /   -------------------------------------------- #

    with col2:
        st.subheader(':red[Delete option]')

        try:
            conn = pymysql.connect(
                host="127.0.0.1",
                user="root",
                password="Mahesh2005",
                database="bizcard_db"
            )

            cursor = conn.cursor()
            cursor.execute("SELECT card_holder FROM bizcardx_data")
            rows = cursor.fetchall()
            names = [row[0] for row in rows]

            cardholder_name = st.selectbox("**Select a Cardholder name to Delete the details**", names, key='delete_cardholder_name')

            session_state = SessionState(data_delete=False)

            st.write('Click the :red[**Delete**] button to delete the selected data')
            delete = st.button('**Delete**', key='delete')

            if delete:
                session_state.data_delete = True

            if session_state.data_delete:
                try:
                    cursor.execute("DELETE FROM bizcardx_data WHERE card_holder = %s", (cardholder_name,))
                    conn.commit()
                    st.info('Data deleted successfully')
                except Exception as e:
                    st.error(f"Error deleting data: {e}")
                finally:
                    cursor.close()
                    conn.close()
                session_state.data_delete = False

        except Exception as e:
            st.error(f"Error connecting to the database: {e}")
