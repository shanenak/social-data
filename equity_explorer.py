import pandas as pd
import streamlit as st

import queries
import utils
import visualization
from constants import STATES, EQUITY_DATA_TABLE, TRANSPORT_DATA_TABLE, LINKS


def census_equity_explorer():
    indent = 4

    st.title('Equity Explorer')
    st.write('''  
            ### Select a Geography
            Identify which census tracts you are interested in exploring.        
            ''')

    col1, col2 = st.columns((1 + indent, 1))
    with col1:
        state = st.selectbox("Select a state", STATES).strip()
        county_list = queries.all_counties_query()
        county_list = county_list[county_list['state_name'] == state]['county_name'].to_list()
        county_list.sort()
        counties = st.multiselect('Select a county', ['All'] + county_list)
        tables = queries.EQUITY_CENSUS_TABLES
        tables = [_.strip().lower() for _ in tables]
        tables.sort()

    if len(tables) > 0 and len(counties) > 0:
        try:
            if 'All' in counties:
                df = queries.latest_data_census_tracts(state, county_list, tables)
            else:
                df = queries.latest_data_census_tracts(state, counties, tables)
        except:
            df = pd.DataFrame()

        if st.checkbox('Show raw data'):
            st.subheader('Raw Data')
            st.caption(str(df.shape))
            st.dataframe(df.iloc[:, 2:])
            st.download_button('Download raw data', utils.to_excel(df), file_name=f'{state}_data.xlsx')
        if 'state_name' in df.columns:
            df = df.loc[:, ~df.columns.duplicated()]
            df['State'] = df['state_name']
        if 'county_name' in df.columns:
            df = df.loc[:, ~df.columns.duplicated()]
            df['County Name'] = df['county_name']
        df.set_index(['State', 'County Name'], drop=True, inplace=True)

        df = queries.clean_equity_data(df)

        st.write('''
                ### Identify Equity Geographies in the Region
                
                "Equity Geographies" are census tracts that may be considered areas of concern. Each of these census tracts meet at least one of the two criteria below. This methodology is based on the equity priority community [methodology](https://bayareametro.github.io/Spatial-Analysis-Mapping-Projects/Project-Documentation/Equity-Priority-Communities/#summary-of-mtc-epc-demographic-factors--demographic-factor-definitions) developed by the San Francisco Bay Area Metropolitan Transportation Commission (MTC).                
                ''')

        col1, col2, col3 = st.columns((5, 1, 5))
        with col1:
            st.write("""
            #### Criteria A
            
            Census tracts have a concentration of BOTH people of color AND low-income households
            """)
        with col3:
            st.write("""
            #### Criteria B 
            
            Census tracts have a concentration of three or more of the remaining six equity indicators AND a concentration of low-income households           
            """)

        with st.expander('List of equity indicators'):
            st.write('''
                     We currently have over 40 tables in the database, representing over 2 million rows of data. The following datasets were used for the equity indicators considered.
                    ''',
                     EQUITY_DATA_TABLE,
                     "For more information on the framework that the criteria is based on, read [here](" + LINKS[
                         'mtc_framework'] + ") for more info.")

        st.write('### View Equity Geographies on Map')
        st.caption('The map below shows all the equity geographies based on the criteria above. '
                   'Scroll over the equity geographies to view which of the criteria is met.')

        concentration = st.select_slider(
            'Limit the number of equity geographies by increasing the concentration requirements',
            options=['Low', 'Medium', 'High'])
        coeff = {'Low': 0.5, 'Medium': 1, 'High': 1.5}

        df, total_census_tracts, concentration_thresholds, averages, epc_averages = queries.get_equity_geographies(
            df, coeff[concentration])

        geo_df = df.copy()
        geo_total = total_census_tracts.copy()
        df_copy = df.copy()
        df.drop(['geom'], inplace=True, axis=1)
        total_census_tracts.drop(['geom'], inplace=True, axis=1)
        geo_df = geo_df[['geom', 'Census Tract']]
        geo_total = geo_total[['geom', 'Census Tract']]

        visualization.make_equity_census_map(geo_total, total_census_tracts, 'Criteria')

        with st.expander('More on how concentrations are defined'):
            st.write('''
                    Equity geographies are compared against concentration thresholds as defined below.
                    ''')
            st.caption('*concentration threshold = average + (standard deviation x coefficient)*')
            st.write('Coefficients default to be 0.5. Coefficients can be increased to 1 or 1.5 to narrow the search.')

        st.write('''
                ### Equity Indicators
                Compare Equity Geographies to the rest of the county for any of the equity indicators. 
                Refer to criteria A and B above for more information on how equity indicators are used to identify Equity Geographies.  
                ''')

        feature = st.selectbox(
            "Equity indicator to compare",
            queries.EQUITY_CENSUS_POC_LOW_INCOME + queries.EQUITY_CENSUS_REMAINING_HEADERS)

        st.write('''
                ### How does the Equity Geography average compare to the county-wide average?''')
        visualization.make_horizontal_bar_chart(averages, epc_averages, feature)

        st.write('### View variation by geography')

        filter_level = st.radio('Filter map for:', ('Equity Geographies only', 'All census tracts in selected region'),
                                key='equity')
        select_data = {'All census tracts in selected region': total_census_tracts, 'Equity Geographies only': df}
        select_geo = {'All census tracts in selected region': geo_total, 'Equity Geographies only': geo_df}

        visualization.make_equity_census_map(select_geo[filter_level], select_data[filter_level], feature + ' (%)')

        if st.checkbox('View data at the census tract level'):
            filter_data = (
                    ['Census Tract'] + ['Criteria'] + [x + ' (%)' for x in queries.EQUITY_CENSUS_POC_LOW_INCOME] +
                    [x + ' (%)' for x in queries.EQUITY_CENSUS_REMAINING_HEADERS]
            )
            st.dataframe(df[filter_data].reset_index(drop=True))
            st.download_button('Download selected data', utils.to_excel(df[filter_data]),
                               file_name=f'{state}_{filter_level}.xlsx')

        tables = queries.TRANSPORT_CENSUS_TABLES
        tables = [_.strip().lower() for _ in tables]
        tables.sort()

        if len(tables) > 0 and len(counties) > 0:
            try:
                if 'All' in counties:
                    transport_df = queries.latest_data_census_tracts(state, county_list, tables)
                else:
                    transport_df = queries.latest_data_census_tracts(state, counties, tables)
            except:
                transport_df = pd.DataFrame()

        transport_df = transport_df.loc[:, ~transport_df.columns.duplicated()]
        if 'state_name' in transport_df.columns:
            transport_df['State'] = transport_df['state_name']
        if 'county_name' in transport_df.columns:
            transport_df['County Name'] = transport_df['county_name']
        transport_df.set_index(['State', 'County Name'], drop=True, inplace=True)

        transport_epc, transport_df, normalized_data, averages, epc_averages = queries.clean_transport_data(
            transport_df, df_copy)

        geo_df = transport_df.copy()
        geo_epc = transport_epc.copy()
        geo_df = geo_df[['geom', 'Census Tract']]
        geo_epc = geo_epc[['geom', 'Census Tract']]
        st.markdown("""---""")

        st.write('''
                ### Equity in Transportation
                
                Analyze behavior and transportation considerations for vulnerable communities in the county.          
                ''')
        with st.expander('More about this dataset'):
            st.write('''
                     We currently have almost 40 tables in the database, representing over 2 million rows of data. The following datasets were used for the transportation indicators considered.
                    ''',
                     TRANSPORT_DATA_TABLE)
        st.write('''
                ### Transportation Considerations in the Region
                
                Compare Equity Geographies to the rest of the county for any of the transportation indicators. Analyze behavior and transportation considerations for vulnerable communities in the county.
                ''')
        feature = st.selectbox(
            "Transportation indicator to compare",
            queries.TRANSPORT_CENSUS_HEADERS)

        st.write('### How does the Equity Geography average compare to the county-wide average?')
        visualization.make_horizontal_bar_chart(averages, epc_averages, feature)

        st.write('### View variation by geography')
        radio_data = st.radio('Filter map for:', ('Equity Geographies only', 'All census tracts in selected region'),
                              key='transport')
        select_data = {'All census tracts in selected region': transport_df, 'Equity Geographies only': transport_epc}
        select_geo = {'All census tracts in selected region': geo_df, 'Equity Geographies only': geo_epc}

        visualization.make_transport_census_map(select_geo[radio_data], select_data[radio_data], feature)

        transport_epc.drop(['geom'], inplace=True, axis=1)
        transport_df.drop(['geom'], inplace=True, axis=1)
        st.write(f'### Equity Geography Census Tracts ({feature}):')

        visualization.make_transport_census_chart(transport_epc, averages, feature)

        st.write('''
                ### Create Transportation Vulnerability Index
                
                Create a framework to identify a subset of the Equity Geographies where there may be a gap in access to transit.
                
                #### Customize the Transportation Vulnerability Index              
                ''')

        selected_indicators = st.multiselect('Select which indicators to use in the Transportation Vulnerability Index',
                                             queries.TRANSPORT_CENSUS_HEADERS,
                                             default=['Zero-Vehicle Households (%)', 'Vehicle Miles Traveled',
                                                      'People of Color (%)', 'No Computer Households (%)']
                                             )

        st.write('''Select weights for each of the selected indicators. Ensure the sum of the weights is 100%.''')
        index_value = {}
        dynamic_col1, dynamic_col2, dynamic_col3 = st.columns(3)
        for i, indicator in enumerate(selected_indicators):
            position = i % 3
            if position == 0:
                with dynamic_col1:
                    index_value[indicator] = st.number_input(indicator, min_value=0, max_value=100,
                                                             value=round((100 / len(selected_indicators))),
                                                             key=indicator)
            elif position == 1:
                with dynamic_col2:
                    index_value[indicator] = st.number_input(indicator, min_value=0, max_value=100,
                                                             value=round((100 / len(selected_indicators))),
                                                             key=indicator)
            elif position == 2:
                with dynamic_col3:
                    index_value[indicator] = st.number_input(indicator, min_value=0, max_value=100,
                                                             value=round((100 / len(selected_indicators))),
                                                             key=indicator)

        if sum(index_value.values()) > 101 or sum(index_value.values()) < 99:
            st.error("Weights must sum to 100")

        st.write('''### Transportation Vulnerability Index''')
        st.caption('Equity geographies are sorted based on each of the transportation vulnerability index values')

        normalized_data = normalized_data.melt('Census Tract', selected_indicators, 'Indicators')
        normalized_data.rename({'value': 'Index Value'}, axis=1, inplace=True)
        normalized_data['Index Value'] = normalized_data['Indicators'].apply(lambda x: index_value[x]) * \
                                         normalized_data['Index Value']
        transport_index = normalized_data.groupby(['Census Tract'])['Index Value'].sum()
        visualization.make_stacked(normalized_data)

        transport_index.sort_values(ascending=False, inplace=True)

        st.write('#### View the census tracts with the highest index values')
        num_tracts = st.slider('Select number of census tracts to view',
                               min_value=1, max_value=len(transport_index),
                               value=[5 if 5 < len(transport_index) else len(transport_index)]
                               )[0]

        selected = transport_index.head(num_tracts).reset_index()
        selected_tracts = transport_epc.loc[transport_epc['Census Tract'].isin(selected['Census Tract'])]
        selected_tracts['value'] = selected_tracts['Census Tract'].apply(lambda x: transport_index.loc[x])
        selected_geo = geo_epc.loc[geo_epc['Census Tract'].isin(selected['Census Tract'])]
        selected_geo['Index Value'] = selected_geo['Census Tract'].apply(lambda x: round(transport_index.loc[x]))

        visualization.make_transport_census_map(selected_geo, selected_tracts, 'Index Value')
        # visualization.make_transit_map(selected_geo, selected_tracts, 'Index Value')

        st.write('''
                #### How are these Equity Geographies most vulnerable?            
                ''')
        st.caption('Select a census tract from the list below to investigate relative transit access and demand.')
        transport_df.set_index('Census Tract', inplace=True)

        col1, col2, col3 = st.columns((1, 1, 1))
        with col1:
            selected_tract = st.radio('Census Tract IDs', selected_tracts['Census Tract'])
        with col2:
            for header in queries.TRANSPORT_CENSUS_HEADERS[(int(len(queries.TRANSPORT_CENSUS_HEADERS) / 2)):]:
                st.metric(header,
                          value=str(round(transport_df.loc[selected_tract, header], 1)) + queries.TABLE_UNITS[header],
                          delta=str(round(transport_df.loc[selected_tract, header] - averages[header], 1)) +
                                queries.TABLE_UNITS[header] + ' from county average')
                st.write('')
        with col3:
            for header in queries.TRANSPORT_CENSUS_HEADERS[:(int(len(queries.TRANSPORT_CENSUS_HEADERS) / 2))]:
                st.metric(header,
                          value=str(round(transport_df.loc[selected_tract, header], 1)) + queries.TABLE_UNITS[header],
                          delta=str(round(transport_df.loc[selected_tract, header] - averages[header], 1)) +
                                queries.TABLE_UNITS[header] + ' from county average')
                st.write('')

        with st.expander('View data at the census tract level'):
            st.caption('Values for selected indicators are shown for the census tracts with the highest index values')
            df = transport_df.loc[(transport_df.index).isin(selected['Census Tract'])][
                queries.TRANSPORT_CENSUS_HEADERS + queries.POSITIVE_TRANSPORT_CENSUS_HEADERS].style.format("{:.1%}")
            st.dataframe(df)
            st.download_button('Download selected tract data', utils.to_excel(df),
                               file_name=f'{state}_selected_transport_data.xlsx')
