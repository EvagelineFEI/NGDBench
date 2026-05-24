结构化数据: 
no_agg:
{
    "template_type": "basic",
    "query": "MATCH (n:Person {birthday: '1982-04-02'})-[:Person_workAt_Company]->(m) RETURN m",
    "clean_answer": [
      "Organisation:650",
      "Organisation:663",
      "Organisation:874",
      "Organisation:813",
      "Organisation:811",
      "Organisation:809"
    ],
    "noise_answer": [
      "Organisation:663",
      "Organisation:874",
      "Organisation:650"
    ],
    "same_as_cleangraph": false,
    "nlp": "Find companies that a person with a birthday on 1982-04-02 works at"
}

agg:
  {
    "template_type": "basic",
    "query": "MATCH (a:Comment) RETURN avg(a.likes) AS avg_value",
    "clean_answer": 33.33193652202874,
    "noise_answer": 4533.92414127121,
    "same_as_cleangraph": false,
    "nlp": "Find the average number of likes for comments"
  },

management:
{
  "steps": [
    {
      "step": 1,
      "operate_query": "CREATE (n:Post {locationIP: '1.2.0.161'})",
      "valid_query": "MATCH (n:Post) RETURN count(n) AS cnt",
      "answer": 1121227,
      "operate_nlp": "Insert a Post node with locationIP '1.2.0.161'",
      "valid_nlp": "How many Post nodes are there?"
    },
    {
      "step": 2,
      "operate_query": "MATCH (n:Post {id: '87.243.45.171'}) DETACH DELETE n",
      "valid_query": "MATCH (n:Post) RETURN count(n) AS cnt",
      "answer": 1121228,
      "operate_nlp": "Delete a Post node with id '87.243.45.171'",
      "valid_nlp": "How many Post nodes are there now?"
    },
    {
      "step": 3,
      "operate_query": "CREATE (n:Post {locationIP: '195.60.83.105'})",
      "valid_query": "MATCH (n:Post) RETURN count(n) AS cnt",
      "answer": 1121228,
      "operate_nlp": "Insert a Post node with locationIP 195.60.83.105",
      "valid_nlp": "How many Post nodes are there in total?"
    },
    {
      "step": 4,
      "operate_query": "CREATE (n:Post {locationIP: '1.2.0.161'})",
      "valid_query": "MATCH (n:Post) RETURN count(n) AS cnt",
      "answer": 1121229,
      "operate_nlp": "Insert a Post node with locationIP '1.2.0.161'",
      "valid_nlp": "How many Post nodes are there?"
    },
    {
      "step": 5,
      "operate_query": "MATCH (n:Post {id: '195.60.83.105'}) DETACH DELETE n",
      "valid_query": "MATCH (n:Post) RETURN count(n) AS cnt",
      "answer": 1121230,
      "operate_nlp": "Delete a Post node with id '195.60.83.105'",
      "valid_nlp": "How many Post nodes are there now?"
    },
    {
      "step": 6,
      "operate_query": "MATCH (n:Post {id: '195.60.83.105'}) DETACH DELETE n",
      "valid_query": "MATCH (n:Post) RETURN count(n) AS cnt",
      "answer": 1121230,
      "operate_nlp": "Delete the Post node with id '195.60.83.105'",
      "valid_nlp": "How many Post nodes are there now?"
    }
  ]
},

judge:
  {
    "type": "nested_loop",
    "template_query": "MATCH (g:Loan)<-[:Account_Repay_Loan]-(n:Account) WITH g, n RETURN g.balance AS collection, collect(n.nickname)[0..1] AS entity",
    "anti_template_query": "MATCH (g:Loan), (n:Account) WHERE NOT (g)<-[:Account_Repay_Loan]-(n) WITH g, n RETURN g.balance AS collection, collect(n.nickname)[0..1] AS entity",
    "contains_noise": true,
    "clean_answer": {
      "valid_answer": [
        {
          "a": 73387855.71,
          "b": "Tamar Sack",
          "judge": true
        },
        {
          "a": 6424948.53,
          "b": "Truman Danson",
          "judge": true
        },
        {
          "a": 38453298.21,
          "b": "Edythe Cappellano",
          "judge": true
        },
        {
          "a": 44685532.09,
          "b": "Kelly Kumro",
          "judge": true
        },
        {
          "a": 49677584.45,
          "b": "Brandon Glausier",
          "judge": true
        },
        {
          "a": 20972870.6,
          "b": "Travis Poortinga",
          "judge": true
        },
        {
          "a": 1635849.9,
          "b": "Latasha Okon",
          "judge": true
        },
        {
          "a": 6169739.23,
          "b": "Jamie Gasner",
          "judge": true
        },
        {
          "a": 9054915.78,
          "b": "Erich Boisen",
          "judge": true
        },
        {
          "a": 20812036.9,
          "b": "Brigitte Hedin",
          "judge": true
        },
        {
          "a": 13096476.3,
          "b": "King Selusi",
          "judge": true
        },
        {
          "a": 12446839.43,
          "b": "Susana Gambrel",
          "judge": true
        },
        {
          "a": 8472157.46,
          "b": "Fermin Kotow",
          "judge": true
        },
        {
          "a": 19528603.49,
          "b": "Ahmad Beile",
          "judge": true
        },
        {
          "a": 65667504.16,
          "b": "Quentin Koenig",
          "judge": true
        },
        {
          "a": 6849793.43,
          "b": "Elenora Acal",
          "judge": true
        },
        {
          "a": 21020545.6,
          "b": "Leonard Burzlaff",
          "judge": true
        },
        {
          "a": 46550552.22,
          "b": "Jeramy Gariti",
          "judge": true
        },
        {
          "a": 7599394.38,
          "b": "Colby Leighton",
          "judge": true
        },
        {
          "a": 2125786.73,
          "b": "Toney Reineman",
          "judge": true
        }
      ],
      "invalid_answer": [
        {
          "a": 24778382.07,
          "b": "Zena Youkhana",
          "judge": false
        },
        {
          "a": 562.45,
          "b": "Zena Youkhana",
          "judge": false
        },
        {
          "a": 179243.54,
          "b": "Zena Youkhana",
          "judge": false
        },
        {
          "a": 16936508.63,
          "b": "Zena Youkhana",
          "judge": false
        },
        {
          "a": 2638.41,
          "b": "Zena Youkhana",
          "judge": false
        },
        {
          "a": 45060144.42,
          "b": "Zena Youkhana",
          "judge": false
        },
        {
          "a": 8409177.2,
          "b": "Zena Youkhana",
          "judge": false
        },
        {
          "a": 6129066.88,
          "b": "Zena Youkhana",
          "judge": false
        },
        {
          "a": 40556909.41,
          "b": "Zena Youkhana",
          "judge": false
        },
        {
          "a": 11479550.46,
          "b": "Zena Youkhana",
          "judge": false
        },
        {
          "a": 893352.9,
          "b": "Zena Youkhana",
          "judge": false
        },
        {
          "a": 19098275.3,
          "b": "Zena Youkhana",
          "judge": false
        },
        {
          "a": 36036447.05,
          "b": "Zena Youkhana",
          "judge": false
        },
        {
          "a": 24982309.1,
          "b": "Zena Youkhana",
          "judge": false
        },
        {
          "a": 20155089.06,
          "b": "Zena Youkhana",
          "judge": false
        },
        {
          "a": 48529320.9,
          "b": "Zena Youkhana",
          "judge": false
        },
        {
          "a": 22379627.55,
          "b": "Zena Youkhana",
          "judge": false
        },
        {
          "a": 14666632.43,
          "b": "Zena Youkhana",
          "judge": false
        },
        {
          "a": 5732707.3,
          "b": "Zena Youkhana",
          "judge": false
        },
        {
          "a": 62530.18,
          "b": "Zena Youkhana",
          "judge": false
        }
      ]
    },
    "noise_answer": {
      "valid_answer": [
        {
          "a": null,
          "b": "Ferdinand CalcutT",
          "judge": true
        },
        {
          "a": 13712068.55,
          "b": "Blair Steidley",
          "judge": true
        },
        {
          "a": 38950944.59,
          "b": "ABdul Hirsch",
          "judge": true
        },
        {
          "a": 5699117.79,
          "b": "Otis Laux",
          "judge": true
        },
        {
          "a": 15604285.48,
          "b": "Lucius Matzinger",
          "judge": true
        },
        {
          "a": 30414220.91,
          "b": "Raleigh Brantley",
          "judge": true
        },
        {
          "a": 27765759.99,
          "b": "IlSe Riiscen",
          "judge": true
        },
        {
          "a": 31967560.38,
          "b": "David Tag",
          "judge": true
        },
        {
          "a": 3977527.9,
          "b": "Robyn Akre",
          "judge": true
        },
        {
          "a": 38459896.9,
          "b": "Annabelle Fromong",
          "judge": true
        },
        {
          "a": 29063321.16,
          "b": "CamieMankoski",
          "judge": true
        },
        {
          "a": 78353579.38,
          "b": "Zane Neidlinger",
          "judge": true
        },
        {
          "a": 46893183.6,
          "b": "Hui Yonke",
          "judge": true
        },
        {
          "a": 15247985.52,
          "b": "Hang Blachly",
          "judge": true
        },
        {
          "a": 261354108.0,
          "b": "Ayana Eggert",
          "judge": true
        },
        {
          "a": 2876749.88,
          "b": "Jonn Crjsp",
          "judge": true
        },
        {
          "a": 26586186.0,
          "b": "Rosalba Wall",
          "judge": true
        },
        {
          "a": 14993298.41,
          "b": "Marlen Pugmire",
          "judge": true
        },
        {
          "a": 14666632.43,
          "b": "Letty Gloss",
          "judge": true
        },
        {
          "a": 5374770.53,
          "b": "Scaarlett Keljihoomalu",
          "judge": true
        }
      ],
      "invalid_answer": [
        {
          "a": null,
          "b": "Signe Unterreiner",
          "judge": false
        },
        {
          "a": 13712068.55,
          "b": "Signe Unterreiner",
          "judge": false
        },
        {
          "a": 38950944.59,
          "b": "Signe Unterreiner",
          "judge": false
        },
        {
          "a": 13823420.97,
          "b": "Signe Unterreiner",
          "judge": false
        },
        {
          "a": 5699117.79,
          "b": "Signe Unterreiner",
          "judge": false
        },
        {
          "a": 15604285.48,
          "b": "Signe Unterreiner",
          "judge": false
        },
        {
          "a": 30414220.91,
          "b": "Signe Unterreiner",
          "judge": false
        },
        {
          "a": 27765759.99,
          "b": "Signe Unterreiner",
          "judge": false
        },
        {
          "a": 31967560.38,
          "b": "Signe Unterreiner",
          "judge": false
        },
        {
          "a": 3977527.9,
          "b": "Signe Unterreiner",
          "judge": false
        },
        {
          "a": 38459896.9,
          "b": "Signe Unterreiner",
          "judge": false
        },
        {
          "a": 29063321.16,
          "b": "Signe Unterreiner",
          "judge": false
        },
        {
          "a": 78353579.38,
          "b": "Signe Unterreiner",
          "judge": false
        },
        {
          "a": 46893183.6,
          "b": "Signe Unterreiner",
          "judge": false
        },
        {
          "a": 15247985.52,
          "b": "Signe Unterreiner",
          "judge": false
        },
        {
          "a": 60505.6,
          "b": "Signe Unterreiner",
          "judge": false
        },
        {
          "a": 261354108.0,
          "b": "Signe Unterreiner",
          "judge": false
        },
        {
          "a": 2876749.88,
          "b": "Signe Unterreiner",
          "judge": false
        },
        {
          "a": 26586186.0,
          "b": "Signe Unterreiner",
          "judge": false
        },
        {
          "a": 158692.7,
          "b": "Signe Unterreiner",
          "judge": false
        }
      ]
    },
    "nlp": "For Loan node g, is the collect n.nickname belongs to Account nodes n that repay the same Loan node g?"
  },

非结构化：
  {
    "template_id": "chain_T002",
    "template_type": "chain",
    "query": "MATCH (a:entity {id: 'active transportation'})<-[:promote *1..5]-(b:entity) RETURN a.id, b.id",
    "answer": [
      {
        "a.id": "active transportation",
        "b.id": "policies"
      }
    ],
    "query_node_ids": [
      "active transportation"
    ],
    "answer_node_ids": [
      "active transportation",
      "policies"
    ],
    "mention_in_nodes": [
      "liance on individual car transportation, like walking and also to spearhead the transition dedicated bike lanes and of public transport networks. zones not only promotes a healthier lifestyle, but also reduces emissions. Figure 34: Example of a microcar. Source: Moses Ogutu, IAP Staff. manufacturing process that can also be adopted by African countries. Still, it is crucial to address potential challenges, such as the need for charging infrastructure for electric microcars and ensuring that these vehicles meet safety standards. Microcars have already been introduced in some African countries including South Africa which has many microcar models. For instance, at the Smarter Mobility Africa Summit, held in South Africa in October 2021, a notable highlight was the showcase of a compact electric microcar by Funky Electric (Piper, 2023). Further cementing this trend, in June 2023, City Blitz, an electric microcar was introduced in the South African market (Droppa, 2023). A shift towards smaller, more efficient vehicles could be particularly relevant in the context of Africa’s urban dynamics. 4.9 Finding and Recommendation Decarbonisation of Transport in Africa: Opportunities, Challenges and Policy Options N O F the interacademy POLICY OPTIONS AND policies and regulations aimed at fostering cleaner transportation alternatives are essential in realising decarbonised and sustainable transport objectives. The policy options and implications explored in this chapter seek to address the broad spectrum of needs and challenges associated with the decarbonisation of transport in Africa. Recognising that no single policy pathway suits all countries in the continent, the adoption and implementation of policies needs to be customised to fit the specific priorities and conditions of each country. Central to the transition towards decarbonised transport, however, is ensuring a just transition, one that is equitable and inclusive for all stakeholders involved. While regulations are essential for driving the decarbonisation of transport in Africa, policymakers must carefully balance the need for environmental protection with considerations of economic viability, equity, and social welfare. Collaborative and inclusive policymaking processes, informed by robust stakeholder engagement and evidence-based analysis, are essential to maximise the positive impacts and minimise the potential drawbacks of regulatory interventions in the transportation sector. Some of the positive impacts’ regulations play in decarbonisation of transport in Africa include emission reduction, promotion of cleaner technologies, creation of conducive environment for investment in sustainable transportation infrastructure and technologies and reduction on reliance on private vehicles and encouragement of modal shifts towards more sustainable modes of transport. However, stringent regulations can impose additional costs on vehicle manufacturers, distributors, and consumers. Distortion of market dynamics hinder competition, leading to inefficiencies and unintended consequences, and limited enforcement capacity and institutional weaknesses that can undermine the effectiveness of regulations aimed at decarbonising transport. 5.1 Disrupting Dominant Regimes in the Transport Sector Policies and processes of decarbonising road transport will result in the disruption of existing and often dominant regimes in the transportation sector. These regimes include the oil or fossil fuel industry, transport sector operators, and the institutions and institutional frameworks that govern these transport systems. Decarbonisation involves reducing dependence on oil and other fossil fuels, which are the primary energy sources for conventional ICE vehicles. Transitioning to low-carbon or zero-carbon alternatives like EVs significantly impacts the demand for fossil fuels. For transport sector operators such as the companies and organisations involved in manufacturing, operating, or maintaining transportation systems, decarbonisation will require them to adopt new technologies, change business models, and comply with different regulations. For instance, car CHAPTER FIVE O F the interacademy Decarbonisation of Transport in Africa: Opportunities, Challenges and Policy will need to shift from producing traditional vehicles to electric ones, while vehicle owners and both private and public service providers will need to acquire new vehicles. Decarbonisation efforts will necessitate new or revised policies, regulations, and incentives to encourage the adoption of cleaner transportation modes. This could disrupt existing institutional frameworks that have traditionally supported existing regimes, such as subsidies that have historically supported the fossil-fuel industry and transport systems or the associated fuel tax revenues for governments (discussed in Section 5.4). Decarbonisation policies inherently challenge the status quo and can lead to significant economic, social, and institutional changes and tensions. The Multi-Level Perspective ( ), a framework for understanding challenges associated with complex sustainability transitions encompassing multiple actors, including businesses, consumers, social movements, policymakers, academia, media, and investors (Geels, 2019) has been applied to assess the speeds and natures of transitions across countries, such as electric mobility in the UK and Germany, and offers a useful lens for understanding the challenges associated with decarbonising transport. Figure 35 depicts the , highlighting its three analytical levels (niche–regime–landscape) and temporal phases (emergence, diffusion, and reconfiguration). This arrangement facilitates the identification and visualisation of influences and interactions across various levels. The argues that for transformative innovations such as EVs to be effectively adopted, some essential factors need to be considered (Medina-Molinaa, et al., 2022). First, it is important to understand the regime—that is the dominant actors, practices, and rules that govern the current system—and the implications of maintaining the existing regime. Second, because the regime constitutes a social and technical system, it is important to Landscape developments put pressure on existing Reconﬁ The regime is dynamically conﬁguration breaks through, of ‘windows of opportunity’. Adjustments occur in networks of actors support innovation on the basis of expectations and visions Learning and experiments take & 35: The multi-level perspective framework for complex sustainability transitions. Source: Adapted from International Science Council (2019)’s adaptation of Geels (2019). N O F the interacademy Decarbonisation of Transport in Africa: Opportunities, Challenges and Policy Options understand how to disrupt the regime and what the associated consequences may be. Disrupting the regime to usher in a more sustainable and decarbonised system may occur, for example, by introducing alternative (and often more sustainable) practices from niche actors or taking advantage of landscape pressures or “shock events” (such as the COVID-19 pandemic). Changes in the global contexts, such as increased awareness of climate change impacts by society, can also provide opportunities for destabilising the regime to allow transition to sustainable solutions. Third, all five subcategories of regimes (policy, science and technology, industry practices, market and user preferences, and culture) need to simultaneously change to transition successfully to a sustainable system. Regimes are typically stable systems and difficult to disrupt for various reasons: the sub-regimes are aligned, mutually dependent, re-enforcing, evolving, and subject to the same set of rules. This points to the importance of niches, which according to the , is where alternative approaches to socio-technical transformation, and innovative practices with potential to transform (change, disrupt, destabilise) regimes occur. Thus, for successful decarbonisation of transport to occur, strategies are needed to address these regime dimensions comprehensively, recognising that focusing on one area (like policy) without considering others (such as technology, market preferences, and culture) is unlikely to yield transformative change. In addition to the business models and solutions discussed in Chapter 2, the policy options and implications presented in this chapter attempt to address most of the identified needs and challenges to decarbonisation of transport in Africa. African countries have unique and differing needs, and no single policy pathway can meet the needs of all countries. The adoption and application of policy pathways for decarbonising transport needs to be tailored to the specific priorities and prerequisites of individual countries. 5.2 Promotion of Electric countries around the world including countries in Africa such as Egypt, Kenya, Mauritius, Rwanda, South Africa, and Uganda have developed policies to promote the use of EVs such as subsidies, tax incentives, and development of affordable and accessible charging infrastructure (see Section 2.1). EVs offer significant cost advantages over ICE vehicles in terms of operating expenses. EVs have lower fuel costs, as electricity is generally cheaper than gasoline or diesel, leading to substantial savings over the vehicle’s lifetime. EVs also have fewer moving components, hence they require less maintenance. As a result of the electric motor’s durability relative to ICEs, they also have longer lifespans. 5.3 Cost-Benefit analysis of Electric Vehicles Compared to Internal Combustion Engine total cost approach is widely utilised to compare the costs of acquiring and operating EVs compared with those of conventional vehicles (Liu, et al., 2021; Wu, et al., 2015). This method aggregates the purchase price and operating expenses, such as maintenance, O F the interacademy Decarbonisation of Transport in Africa: Opportunities, Challenges and Policy replacement, energy, fuel, financing, and insurance costs for various electric mobility modes — including cars, buses, and two-wheelers — and contrasts them with their conventional counterparts. Additionally, it factors in the external benefits and costs associated with decarbonisation, such as environmental and health impacts. To enable cross-country comparisons, the total costs are adjusted for taxes and subsidies, which significantly affect the final acquisition and operational expenses of EVs. Table 6 applies the total cost approach to provide a comparative cost-benefit analysis of EVs versus ICE vehicles, using Thailand as a case study (Suttakul, et al., 2022). Table 6: Comparing cost elements for electric and internal combustion engine vehicles in Total Cost of Ownership (TCO) (USD) Deprecation Cost (USD) (USD) (USD) (USD) Engine (ICE) 61,190.00 26,311.70 23,864.10 611.90 10,402.30 Vehicles (HEV) 54,940.00 29,118.20 13,735.00 1,098.80 10,988.00 (PH)EV 55,940.00 33,564.00 7,831.60 2,797.00 11,747.40 Vehicles (BEV) 60,890.00 34,098.40 6,089.00 10,960.20 9,742.40 Note: Depreciation cost reflect capital cost for the vehicle over its life cycle. Source: Suttakul, et al. (2022) Table 6 compares the costs of owning and operating an ICE vehicle against three types of EVs over a 15-year period: hybrid electric vehicles (HEVs), plug-in hybrid electric vehicles (PHEVs), and battery electric vehicles (BEVs). HEVs combine a petrol engine with a battery-powered electric drivetrain without plug-in capability. PHEVs feature both a petrol engine and an electric drivetrain, with the ability to recharge via plug-in. BEVs are fully electric with plug-in charging but do not use petrol. The analysis shows that while BEVs vehicles have a higher initial cost, over a 15-year horizon they have a marginal cost advantage over ICE vehicles (60,890 vs 61,190). However, BEVs offer substantially lower energy costs, at just a quarter of that of ICE vehicles, with battery costs —18% of total EV costs — being the main expense. With O F the interacademy Decarbonisation of Transport in Africa: Opportunities, Challenges and Policy Options advancements in EV and battery technology, the costs associated with depreciation and batteries are expected to decrease, making BEVs much more economical than ICE vehicles. This shift will likely ease the transition to BEVs, assuming other concerns, such as range anxiety and infrastructure limitations, are addressed. Currently, HEVs and PHEVs face a cost advantage of USD 6,250 compared to ICE vehicles, aznd this gap is expected to widen as the technology becomes more affordable. It should be noted that Table 6 focuses only on direct costs which include maintenance, battery replacement, energy and fuel, financing, insurance, and related expenses. The direct costs do not account for the environmental and social implications associated with using either type of vehicle, which are significant factors in the push for decarbonisation to mitigate emissions and advance the global climate agenda. These broader impacts are detailed in Table 7 in this section, and Appendix A, both of which compare the national aggregate cost advantage of EVs in select African countries. Table 7: National aggregate cost advantage of electric vehicle adoption in select African countries by Cost Advantage (USD) Capital (USD) Operating (USD) Subtotal (USD) Externality (USD) Cost Advantage (Economic Analysis) (USD) Net taxes subsidies (fiscal wedge) (USD) Economic wedge (USD) Egypt -4107 -1512 -3017 -4330 -1112 -2762 : Briceno-Garmendia, et al. (2023) Although the upfront capital costs of acquiring EVs are high, these vehicles typically have a lifespan of around 15 years. Hence, the costs and benefits are calculated over this period using the World Bank’s approved discount rate of 7% (Briceno-Garmendia, et al., 2023). Egypt and Nigeria face the highest costs in providing charging infrastructure, translating into higher capital costs compared to countries like Ethiopia and Rwanda. The capital cost differential for EVs ranges from USD 5,112 in Rwanda to USD 13,010 in Egypt, relative to the cost of acquiring and operating an equivalent ICE vehicle, which spans between USD 10,000 to USD 20,000 for the countries examined. Initially, acquiring an EV is at least 10% more expensive than an ICE vehicle, but this gap narrows to 5% when considering positive fiscal incentives such as lower EV taxes. In Ethiopia, the fiscal incentives are so substantial that they eliminate the cost disparity between EVs and ICE vehicles. N O F the interacademy Decarbonisation of Transport in Africa: Opportunities, Challenges and Policy are preferred for their minimal emissions, which translates to significant environmental and social benefits over ICE vehicles. These benefits, or externalities, are computed and presented in column 6. When these external benefits are added to the operating costs of EVs, the net cost advantage under the 30x30 decarbonisation scenario target becomes positive for all countries studied. Egypt, in particular, sees higher external benefits due to its dense population. This scenario posits a net social advantage in acquiring and operating EVs, supporting the goal of 30% of new cars and buses and over 70% of two- and three-wheelers being electric by 2030. The fiscal benefits of adopting EVs, which result in lower taxes for importers compared to ICE vehicles, range from USD 8,348 in Egypt to USD 23,592 in Rwanda, where favourable taxes on EVs significantly reduce their purchase price compared to ICE vehicles. The Rwandan case shows how effective fiscal policies can internalise environmental costs to promote electric mobility, sustainability, and social inclusion through improved health outcomes. Similar to four-wheeled electric vehicles (EVs), electric motorcycles offer notable cost savings compared to their fossil-fueled counterparts. These savings manifest across various operational aspects, highlighting the financial benefits of adopting electric mobility in two-wheeled transportation. One of the most significant areas of savings is in energy (fuel vs. electricity), service and maintenance costs. Data based on models like the Roam Air — an electric motorcycle — illustrate a marked reduction in these expenses (see Table 8). Electric motorcycles incur service and maintenance costs of just USD 0.035 per 10 kilometres, a stark contrast to the USD 0.05 per 10 kilometres required for traditional motorcycles. This represents a 33% reduction in service and maintenance expenses, a saving attributed to the simplified mechanical design of electric vehicles. The reduction in service and maintenance expenses increases over the product lifetime from 33% up to 70%, due to faster deterioration of parts requiring lubrication and higher vibrations in fossil fuel vehicles. The absence of conventional engine components reduces the need for regular oil changes and minimises the number of moving parts susceptible to wear and tear. Moreover, the operational or running costs of electric motorcycles further emphasise their economic advantage. Operating at a cost of only USD 0.08 per 10 kilometres, electric motorcycles present a significantly cheaper option than fossil-fueled motorcycles, which have running costs of USD 0.288 per 10 kilometres. This 68% reduction in running costs can accumulate to substantial long-term savings for owners, particularly beneficial for those who frequently rely on their motorcycles for daily commutes or leisure. Table 8: Comparing cost elements for electric vs fossil fueled Fossil Fueled Service & Maintenance Cost (per 10 KM) USD 0.05 USD 0.035 33% (CO2 per KM) 27g 0g 97% Cost (per 10 KM) USD 0. 0.08 68% reduction O F the interacademy Decarbonisation of Transport in Africa: Opportunities, Challenges and Policy Options In conclusion, a cost-benefit analysis that encompasses environmental and social costs can powerfully inform public policy options and the design of optimal fiscal incentives for promoting electric mobility. It underscores the critical role that fiscal and monetary policies play as economic instruments in fostering electric mobility and the decarbonisation of transport, both in Africa and beyond. 5.4 Minimising Tax Revenue Losses Fuel tax losses represent one of the biggest challenges for most governments with the transition to EVs. In January 2022, the United Kingdom projected losses of about USD 6.8 billion annually in fuel duty within eight years due to the transition to EVs (Goodrich, 2022). As fuel duties comprise approximately a third of yearly revenues in the country, this posed a great threat to the tax income used to enhance, operate, and maintain motorways, with EVs already representing over 10% of the domestic vehicle market. Similarly, fuel is an important tax revenue base in many African countries. For instance, the government of Ghana collects eight different taxes on each litre of fuel sold. These comprise of levies for energy debt recovery, energy fund, energy sector recovery, price stabilisation and recovery, road fund, sanitation and pollution, special petroleum tax and unified pricing petroleum fund (Acheampong, 2022). The fuel pump price is therefore higher for Ghanaian motorists at about USD 1.14 per litre, relative to those paid by motorists in Nigeria (USD 0.169), Togo (USD 0.91), and Ivory Coast (USD 1.076) (Goodrich, 2022). Reduced consumption of fuel through the introduction of EVs would thus result in reduced tax income. While some governments may hesitate to adopt EVs due to this reduction, the lost income can be recovered by shifting tax handles to alternative broad-base taxes, such those on telecommunication and mobile financial services. Governments will get more revenues through the surge in electricity purchases to charge EVs and the import taxes of EVs. Other compensating revenue sources would include increasing carbon taxes on hydrocarbons uses and excise duties, road taxes, and other levies on motor vehicles more generally where a motor vehicle becomes a new alternative tax base. Road pricing schemes in which motorists pay based on the time, distance and location travelled can also be adopted. In this case, road toll fees can be an alternative compensating tax base for fuel. African governments heavily subsidise fossil fuels, at an average cost of 1.4% to cushion consumers against rising global oil prices. But this creates heavy fiscal debt. For instance, Nigeria spent more than USD 30 billion on fuel subsidies in the past 15 years, resulting in a significant budget deficit (Goodrich, 2022). On the other hand, Kenya’s petroleum expenditure in 2021 was about USD 2.6 billion, widening the trade/ balance of payments deficit (Brookings, 2023). If EVs can gain traction in these countries, government spending could be channelled away from fossil fuel subsidies towards other sectors such as clean energy development and other poverty reduction initiatives. Oil producing countries like Angola, Equatorial Guinea, and Nigeria may be hesitant about global and continental phase-out of ICEs in the near future because of the need to safeguard the oil exports that sustained their economies. In 2019, the Nigerian senate unanimously rejected a bill which sought to phase out ICEs by 2035 (IOA, 2022). While O F the interacademy Decarbonisation of Transport in Africa: Opportunities, Challenges and Policy that seek to regulate petroleum products such fuel prices will remain fraught with economic and political contestations, in the longer term, EVs are expected to replace ICE vehicles, leaving oil-producing countries with no choice but to support the adoption of EVs and pursue other pathways for diversifying petroleum value chains away from fossils. Besides, there are numerous uses of oil and gas apart from its use as fuels for transportation, electricity generation, and in industries. 5.5 Transport Sector Governance, Institutional Framework and Policy Ownership A major challenge in governing road transportation in Africa is the absence of sustained actions and long-term strategic planning in the sector (Sustainable Mobility for All, 2022). Often, national and subnational governments struggle to effectively tackle mobility issues due to a lack of comprehensive planning. Moreover, even when such plans are in place, their implementation is frequently inadequate. It is common for new plans to be introduced, only to be replaced when a change in administration occurs. The incoming authorities often disregard the efforts made by their predecessors and hastily modify or halt ongoing programmes rather than sustain them for political expediency. Furthermore, the effectiveness of these programmes is hindered by the lack of coordination and monitoring among the various entities involved in road transport (Sustainable Mobility for All, 2022). Responsibilities are frequently dispersed among different national, subnational, metropolitan, or local entities without clear delineation, leading to confusion, neglect, and even duplication of roles leading to inefficiencies in programme implementation. These factors contribute to an environment where private stakeholders can easily overstep boundaries and take advantage of the poorly regulated context. One way to address these challenges is to establish a transport planning and regulatory metropolitan agency, particularly for major cities and metropolitan areas. This institution would assume the role of the lead authority for transport planning, regulation of public transport supply, and improvements to the transport system, including parking and traffic management. Examples of successful initiatives include the Lagos Metropolitan Area Transportation Authority (LAMATA), which has broad powers and independent resources over transport planning in Lagos, Nigeria. LAMATA is recognised for reviving a previously dysfunctional and unregulated transport system (Gomez-Ibanez, 2015). The implementation of such agencies can be difficult, and strong political commitment and sufficient resources are necessary to ensure their effectiveness. African countries have also explored the formation of regional transport infrastructure agencies encompassing several countries including the establishment of the African Association of Urban Transport Authorities (AAUTA) in February 2023 (Kaori & Malgrace, 2023). The initiative emerged through a collaboration between The Greater Abidjan Urban Mobility Authority (AMUGA), or Autorité de la mobilité urbaine dans le Grand Abidjan, and the Africa Transport Policy Program (SSATP), which is an international partnership administered by the World Bank (Niina & Annin, 2023). The AAUTA brings together over 40 urban transport leaders from 13 African countries. It aims to serve as a O F the interacademy Decarbonisation of Transport in Africa: Opportunities, Challenges and Policy Options dedicated platform for African urban transport authorities (UTAs) to meet and exchange lessons learnt and good practices related to planning, coordinating, regulating, financing and managing urban transport systems, and promote public-private partnerships that provide the best conditions for mobilising resources and strengthening cooperation with partners in development (Kaori & Malgrace, 2023). Regional initiatives such as these can foster learning and collaboration in transport sector governance across Africa, especially in the context of the renewed urban designs that are necessary to accommodate electric mobility. In addition to the AAUTA initiative, city authorities can also follow the example of the C40 Cities Climate Leadership Group, which unites 96 cities globally in a concerted effort to combat climate change. Through this platform, cities share strategies, innovations, and actionable plans, thereby cultivating a global network of municipal leaders committed to the reduction of greenhouse gas emissions and the development of resilient, low-carbon urban environments. The C40 initiative demonstrates the potential of collaborative platforms to inspire similar efforts within Africa, thereby enhancing the continent’s capacity for transport decarbonisation. By leveraging collective expertise and initiatives, such collaborations can drive significant progress in regional sustainable development efforts. 5.6 Investments in Public in public transport systems such as mass rapid transit modes (light rail and bus rapid transit (discussed in Section 4.6) are an effective way of reducing carbon emissions in the transport sector. Cities across the world, in both developed and emerging economies such as Bogota (Colombia), Sao Paulo (Brazil), and Jakarta (Indonesia) have invested in these systems, and have seen significant emissions reductions and improved public transportation. To benefit from the environmental and social benefits associated with public transportation s",
      "ystems such as mass rapid transit, countries need to: Prioritise investment in public transit infrastructure: Investing in public transit infrastructure, such as bus rapid transit ( ) systems, light rail, and commuter rail, can significantly improve public transit in Africa, in turn reducing transport sector emissions as populations reduce reliance on personal cars. Countries such as Ethiopia, Kenya, and Tanzania have already made progress in this area by investing in systems, expanding existing rail networks, and building new commuter rail systems (as discussed in Section 4.6). Develop integrated transportation systems: Integrated transportation systems connect different modes of transportation, such as buses, taxis, and trains, and improve the efficiency and convenience of public transit. Cities such as Lagos, Nigeria, have implemented integrated transportation systems that allow passengers to use a single ticket to access multiple modes of transportation (AfDB, 2019), making it convenient and attractive to users. Encourage public-private partnerships: Public-private partnerships can help increase private investment in public transit and improve the quality of service and innovation in transport systems. For example, in Rwanda, the government has partnered with private companies to establish a new dedicated bus lanes ( ) system. Dedicated O F the interacademy Decarbonisation of Transport in Africa: Opportunities, Challenges and Policy lanes for public transport in the country are expected to be operational on a pilot basis in mid-2024 ( Africa, 2023). Public-private partnerships have successfully been utilised to enhance public transport systems around the world, including in infrastructure financing and development. Prioritise safety and security: Improving safety and security of public transit systems can help to increase ridership and improve the overall perception of public transit. Measures such as installing cameras, hiring security personnel, and improving lighting in and around transit stations can help to enhance safety and security (Lierop & El-Geneidy, 2016). Implement innovative fare collection systems: Implementing innovative fare collection systems, such as smart cards and mobile payments, can help to improve the efficiency and convenience of public transit. For example, Kenya has proposed to implement a smart card system for its upcoming system, which could help reduce fare evasion and improve the overall customer experience (The World Bank, 2017). 5.7 Investments in Renewable vehicles could maximise their contribution towards decarbonisation efforts if the electricity used for charging them comes from renewable energy sources such as geothermal, hydroelectric, solar, wind power or biofuels. Africa is naturally endowed with these renewable energy sources. For instance, hydropower is widespread, particularly in east and central Africa, with countries like Ethiopia and the Democratic Republic of Congo harnessing river systems to generate hydroelectricity. Solar and wind power are also increasingly being utilised due to Africa’s abundant sun and favourable wind conditions, especially in the north and in parts of East Africa. Geothermal energy is also being tapped in the Rift Valley, notably in Kenya, which is the top geothermal power producer in Africa. Increased adoption of EVs can drive the demand for cleaner energy, acting as a catalyst for further investment in renewable energy infrastructure. Increased adoption of EVs can also create a positive feedback loop, where the growth of e-mobility spurs decarbonisation of the electric grid itself. In addition to supporting regulation, investments in renewable energies can be enhanced through innovative financing mechanisms such as green bonds, which are specifically destined for the funding or refunding of green projects — that is, projects that are sustainable and socially responsible in areas as diverse as renewable energy, energy efficiency, clean transportation or responsible waste management (AfDB, 2019). Off-grid energy solutions that provide electricity independently of the traditional centralised electrical grid can also serve areas where it is either too expensive or impractical to connect to the grid. Examples of common off-grid energy solutions include solar photovoltaic systems, wind turbines, micro-hydro power, biomass and biogas systems, battery storage systems, and hybrid systems that combine two or more of power systems to ensure a consistent and reliable power supply. Off-grid solutions are crucial for enhancing energy access in remote or underserved areas and are also a part O F the interacademy Decarbonisation of Transport in Africa: Opportunities, Challenges and Policy Options of the strategy for many regions to increase the use of renewable and sustainable energy sources (Nyarko, et al., 2023). 5.8 Promote Non-Motorised -motorised transport ( ) such as cycling, walking, and other human-powered transport can significantly reduce carbon emissions in the transport sector. Many cities in Europe have invested in cycling infrastructure, such as bike lanes and bike parking facilities, which have encouraged people to cycle instead of drive. A study by the European Cyclists’ Federation (ECF) found that increased cycling could reduce carbon emissions from the transport sector by up to 10% by 2050 (European Cyclists’ Federation, 2015). , especially walking, is the dominant mode of transport in Africa, since between 33% and 90% of trips are made as a pedestrian (Sub-Saharan Africa Transport Policy Program (SSATP), 2015). Walking is popular in Africa because of many factors including favourable weather, short trips, poverty, and the high cost of private and public transit (Hernandez, et al., 2021). Figure 36 compares modes of transport in Nairobi, the capital city of Kenya. Walking Public transport (Bus/minibus/ matatu) -wheeler (Bodaboda) Own private -wheeler *Bajaj/Tuktuk) Own Ofﬁce Taxis (Uber, Bolt) Daily 1–2/3–4 days a week 1–3 days a month/ Once a month 1–2 times a 90% 3% 3% 30% 13% 7% 49% 10% 84% 4% 2% 19% 7% 3% 3% 68% 8% 21% 23% 5% 43% 2% 81% 8% 2% 6% 3% 13% 1% 56% 25% 5% 91% 3% 2% 3% 1% 95% 2% 1% Figure 36: Modes of transport used in Nairobi, : Mitullah (2023) infrastructure remains underdeveloped in Africa. In many countries, it is common to find pedestrians walking across and along major arterials and highways, as there are often no secondary roads that could be used as an alternative. When infrastructure such as footpaths are available they are sometimes poorly designed or frequently , leading to secondary problems such as inaccessibility for people with mobility challenges (e.g., those in a wheelchair or with a walking stick) drainage problems, inadequate lighting, and poor landscaping that make them unsafe or unattractive for users (Vanderschuren, et al., 2022). Figure 37 shows a finished walkway in Nairobi; instead of the pathway being located on the sides of the road, it is in the centre of a busy road, forcing pedestrians to cross the street to utilise it (IDS-VREF MAC study 2020–2021, pedestrians in Nairobi). N O F the interacademy Decarbonisation of Transport in Africa: Opportunities, Challenges and Policy who opt for non-motorised transport thus suffer from challenges such as road injuries and fatalities. Africa has the highest proportion of pedestrian and cyclist deaths, accounting for 44% of the total number of road deaths (United Nations, 2023). Many of these can be prevented by implementing policies that promote NMTs. policies in Africa, though increasing, are limited to a few countries. As Figure 38 illustrates, policies are either adopted at the national level (for example, as part of a national transport master plan) or sub-national level (for example, by a local city), with some countries having both. African countries can adopt and improve non-motorised transport in several ways including: Developing a cycling and walking infrastructure that is safe, comfortable, and accessible: Providing dedicated and well-designed bike lanes and pedestrian paths can encourage more people to walk and cycle. Amsterdam and Copenhagen have shown that investing in cycling infrastructure can result in significant increases in the number of people cycling (Pucher & Buehler, 2008). Access to high-quality bike lanes is key since it can enhance a shift to a near-zero carbon form of transport and improve the health and safety of people. A study of European cities found that even occasional cyclists (once or twice weekly) had 84% lower CO2 emissions per person from all daily travel than non-cyclists (Systems Change Lab, 2023). The study noted that if 10% of the population was to change travel behaviour from driving to cycling, emissions from transportation would be expected to drop by about 10%. Implementing policies that support active transportation: Governments can implement policies such as active transportation plans, complete streets policies, and incentives for employers to promote active transportation. Complete streets is a transportation policy and design approach that requires streets to be planned, designed, operated, and maintained to enable safe, convenient, and comfortable travel and access for all anticipated roadway users, regardless of their age, Figure 37: Pedestrian footpath in Nairobi, : Moses Ogutu, IAP. N O F the interacademy Decarbonisation of Transport in Africa: Opportunities, Challenges and Policy Options abilities, or mode of travel. This can help create a culture of walking and cycling and encourage more people to choose active modes of transportation. One such example is Rwanda (see Case Study 3). Moreover, African countries should design manuals for urban areas to mainstream proven practice street designs that promote the use of sustainable modes of transport and enhance the safety of vulnerable road users like cyclists and pedestrians. Involving the community in planning and design: Engaging with the local community and understanding their needs and preferences is essential when planning cycling and walking infrastructure. This can help ensure that the infrastructure is designed to meet the needs of the community and is, therefore, more likely to be used by people. Figure 38: Non-motorised policies in African : Adapted from Collaboration for Active Mobility in Africa O F the interacademy Decarbonisation of Transport in Africa: Opportunities, Challenges and Policy Options Encouraging multi-modal transportation: Encouraging people to use a combination of transportation modes can help reduce car use and increase the use of walking and cycling. Providing facilities such as bike parking and bike share schemes can encourage people to combine cycling with public transportation. Paths and crossings should also be cogniant of the specific needs of women, children, and the elderly. Addressing safety concerns: Addressing safety concerns is crucial for encouraging more people to walk and cycle. This can be achieved through infrastructure improvements such as well-lit paths and crossings. 5.9 Technology and Innovations for Sustainable Mobility Technology transfer is key to driving innovation and the shift to sustainable transport in Africa, particularly in regard to the adoption of electric vehicles (EVs) and related infrastructure. Technology transfer in transportation is giving rise to new forms of flexible, shared mobility and on-demand services. The use of such technologies has enabled the integration of multiple transportation modes in Africa and is facilitating more environmentally friendly, predictable, and high-volume trips. To scale and achieve this technology transfer in transportation in Africa, it is essential to create partnerships between developed countries which are early adopters of EVs, and emerging African countries. These collaborations would facilitate access to EV technologies, including those under copyright protections, crucial for decarbonising transport globally. African transport tech startups are at the forefront of this sustainable transition, with more than 500 startups active across the continent (Briter Bridges, 2023; GSMA, 2023). These startups have attracted significant investment, securing around USD 1.4 billion over the past four years, primarily in passenger solutions, multi-tier systems, and logistics services (GSMA, 2023). They are not only the third most attractive sector in Africa’s startup landscape, but are also pivotal in offering solutions to the continent’s transportation challenges, focusing on reliability, affordability, and reduced carbon emissions. These startups such as Roam in east Africa (see Case study 7 in this Section) are often adapting foreign technologies to suit local conditions, terrains, environmental challenges, and infrastructure needs. Despite their innovative approaches, including the use of intelligent transport systems and big data analytics, these startups face considerable challenges like inadequate infrastructure, funding shortages, and limited managerial expertise (Dosso, 2022). Skilled roles such as design engineers and solar technicians are scarce, often leading startups to depend on expatriate talent. To overcome these barriers and continue advancing, it is crucial for these startups to engage in long-term research and development, partnerships that integrate advanced knowledge and technologies from established companies and research institutions. While policy support in Africa is gradually improving, sustainable mobility startups still struggle to obtain localised data on market practices and demands. Intervening policy is needed to encourage and support these startups. N O F the interacademy Decarbonisation of Transport in Africa: Opportunities, Challenges and Policy Options Case Study 7: Roam, electrifying motorcycles in buses and the popular two-wheelers (motorcycles or motor taxis) are the main public transport vehicles serving the growing population of African cities but are also some of the highest carbon-emitting vehicles on the market (SitatiI, et al., 2022). Founded in 2017, Roam is an East Africa based company with the vision of electrifying the African transport and energy systems. Roam initially focused on electric conversions, converting ICE vehicles to EVs, but later evolved to provide tailored solutions to meet local market demand through business segments that now include an electric motorcycle ( ) designed in Kenya and tailored for Africa (Roam Air); electric bus production for Kenyan and African public transport sectors (Roam Transit), which produces the Roam Move and Roam Rapid; off-the-shelf energy and charging products (Roam Energy & Charging); and tailored software applications to fleet owners, business operators, financiers and others that includes a mobile application for chargers and transactions (Roam Canopy). Roam’s research found that ownership of the battery and the system increases product lifetime, providing the best performance and the lowest total cost of ownership. In the case of motorcycles (Roam Air), the company provides each user with a home charger that allows users to charge at home and anywhere at any time (Figure 39). The company also established ROAM Hubs, multi-purpose electric charging stations that act as an ecosystem solution for motorcycle operators. The hubs offer battery rental services and public charging access, and are outfitted with after-sales support, including spare parts and maintenance services provided by skilled technicians. Figure 39: A motorcycle rider charging his own battery at a Roam : ROAM (2024) O F the interacademy Decarbonisation of Transport in Africa: Opportunities, Challenges and Policy Options 5.10 Just Transition decarbonisation of the economy is reshaping labour markets and workforce skills in complex and dynamic ways, influenced by global trends like technological advancements and demographic changes (International Labour Organisation, 2022). As e-mobility is increasing, various segments of the conventional automobile value chain, spanning manufacturing, sales, and service sectors will become obsolete or undergo significant transformations. These changes are likely to result in job losses in the conventional ICE vehicle industry, while at the same time creating new job opportunities in the EV industry. This transition will require upskilling existing workers and training new ones. In Africa, where many transport jobs are informal, workers often lack social safety nets and access to essential resources like credit or insurance, which will make it challenging for them to adapt their business models to these changes. To ensure socially equitable and inclusive outcomes alongside environmental sustainability, Africa needs to ensure that the transition to a net-zero economy follows a just transition approach. A just transition through social justice has been recognised as a fundamental precondition for sustainable transport (Bongardt, et al., 2023). According to the International Labour Organisation, (ILO) a just transition means greening the In line with the goal of achieving climate impact with speed and scale, home charging allows for deployment without the need for capital intensive charging infrastructure. Public infrastructure can be used assupport, rather than as a necessity. The lower cost of this strategy lowers operating cost by 28% to the end user. The motorcycle components subject to maintenance have been designed to be serviceable with common ICE components. This allows owners to have flexibility and low cost in maintenance. In addition, the hubs serve as public access locations for software and technology updates on the motorcycles making them one-stop-shops for the varying needs of the operators. The hubs are open to other EV players, with several already leveraging this infrastructure today. This open EV platform enables the industry to scale faster, reducing the higher amortisation of closed architecture charging infrastructure being pushed to the end user. Roam’s electric motorcycles have made a notable environmental impact, with each kilometre driven on the Roam Air mitigating 58 g/CO2e. The social and economic impacts are equally significant, with every dollar invested in Roam generating a social return of $2.4 through reduced ownership costs and increased income for users. Over 3 million kilometres have been covered by Roam’s electric motorcycles, underscoring the widespread adoption and effectiveness of their solutions. Roam’s journey has yielded valuable insights, including the importance of vertical integration, the demand for low-cost ownership, and the effectiveness of designing for local conditions. The higher upfront cost remains the primary barrier to faster adoption rates. However, the significantly lower operational costs ensure a more affordable total cost of ownership in the long run. Overcoming this barrier requires achieving economies of scale, possible through innovative financing methods such as non-dilutive funding, debt, first-loss guarantee funds, and carbon financing. N O F the interacademy Decarbonisation of Transport in Africa: Opportunities, Challenges and Policy Options economy in a way that is as fair and inclusive as possible to everyone concerned, creating decent work opportunities and leaving no one behind (ILO, 2021). Just transitions involve maximising the social and economic opportunities of climate action, while minimising and carefully managing any challenges—including through effective social dialogue among all impacted groups, and respect for fundamental labour principles and rights. Ensuring a just transition is important for all economic sectors, including transport. The ILO’s “Guidelines for a Just Transition towards Environmentally Sustainable Economies and Societies for All” (ILO, 2015) highlights key principles for effective transport decarbonisation, and just transition, including: Safeguarding worker rights: A just transition places a strong emphasis on safeguarding workers’ rights and livelihoods during the transition. It advocates for retraining and reskilling programmes, fair employment opportunities in emerging sectors, and maintaining social protections. As decarbonisation of transport will result in job losses and demand new skills, governments, private sector, non-governmental organisations and other stakeholders need to work together to implement programmes to support workers in the transport sector. Ensuring stakeholder participation, equity, and inclusion: A just transition prioritises social equity and inclusion, ensuring that no group or population is disproportionately burdened or excluded from the benefits of the transition. This involves paying particular attention to marginalised and vulnerable groups, including women, indigenous communities, low-income populations, and residents of rural areas. It aims to correct historical inequalities, promote equal opportunities, and ensure fair cost and benefit distribution. Historically, the transport system has not addressed the safety of women or equity between women and men in the transport workforce (International Transport Forum, 2022). Moreover, persons with disabilities and older persons (PWDOD) also have unique challenges that hinder their mobility and access to effective transportation services. In Africa, key transport issues affecting PWDOD include inaccessible infrastructure like missing sidewalks, ramps, and elevators, especially for wheelchair users, a lack of vehicles adapted for their needs, and insufficient awareness among transport staff about their requirements. Lack of accessible transport significantly hinders persons with disabilities and older persons from participating in economic activities, as evidenced by the Kenya Integrated Household Budget Survey (KIHBS) 2015/2016, which revealed that over half of the persons with disabilities in both urban and rural areas face mobility-related challenges that impede their ability to engage in work or access education and welfare services, thus isolating them from critical societal functions and opportunities for economic independence (KIPPRA, 2020). The move towards decarbonisation of transport in Africa offers a chance to improve inclusivity and accessibility for these groups. Solutions include developing infrastructure with features like ramps and elevators at transportation hubs, upgrading vehicle fleets with accessibility features especially for new EVs, integrating technology for enhanced access, and increasing awareness and training among transport operators and staff. An example of this includes South Africa’s MyCiTi Integrated Rapid Transport System in Cape Town. MyCiTi stands as the first universally accessible O F the interacademy Decarbonisation of Transport in Africa: Opportunities, Challenges and Policy system in Sub-Saharan Africa that explicitly prioritised universal accessibility from its inception by integrating all the essential features to accommodate passengers with various mobility needs. These universal access features include tactile paving to assist visually impaired individuals in navigating to stations and platforms, induction loops at ticket kiosks for the hearing impaired, and surveillance both on buses and at stations for enhanced security. Additionally, the service offers boarding bridges on buses along residential and central city routes, ensuring level access from bus stops directly onto the buses for those who need it (DiSA, 2024). Integrating Sustainable Development Goals: A just transition recognises the interconnection of social and environmental challenges and seeks to address them concurrently, promoting a holistic approach to sustainability. This involves integrating decarbonisation policies with broader socio-environmental actions for cohesive and effective sustainability strategies, as discussed in Chapter 4. The Sustainable Mobility for All (SuM4All) Partnership, a global initiative for international cooperation on transport and mobility issues advocates for the integration of just transition principles in sustainable mobility in developing countries in areas such as governance, equity and climate finance (SuM4All, 2022). It emphasises the need to develop transport systems and policy priorities to achieve the greatest socioeconomic benefits for all and notes that even though high-income countries have incentivised the purchase of EV passenger vehicles through purchase subsidies, this approach may not be applicable in low-income African countries. Since the upfront capital costs of EVs are relatively high, limiting their uptake at scale in low-income countries in Africa, the SuM4All partnership suggests that in some countries, a push towards EV adoption can be delayed until supporting infrastructure and ecosystem are developed. Therefore, scarce public resources should instead be focused on improving the transport system through measures like the provision of adequate, safe, comfortable, inclusive, and sustainable public transport (SuM4All, 2022). 5.11 Sustainable Electric Vehicle Supply and Value Chains The principal materials used in the production of EVs and EV batteries such as cobalt, lithium, and nickel, continue to be in short supply as demand and prices increase. The price of lithium rose seven-fold between 2021 and 2022 (IEA, 2022). EVs use batteries, and most EVs require six times the amount of minerals a non-electric car requires (IEA, 2022). Africa has a large concentration of the minerals required to manufacture EVs, including global deposits of cobalt (54%), manganese (46%), bauxite (24%), graphite (21.2%) and vanadium (16%) (Anon., n.d.). The Democratic Republic of Congo ( ) alone accounts for 70% of the world’s cobalt production and more than 50% of the world’s reserves (Anon., n.d.). Nevertheless, despite the continent’s vast reserves, it remains a net exporter of the minerals, largely operating the primary stage of the mineral value chain (mining), approximated at USD 8.8 trillion by 2025 (Anon., n.d.). For African countries to participate effectively in the EV value chain, they will need to break their overdependence on mineral exports by establishing more value by O F the interacademy Decarbonisation of Transport in Africa: Opportunities, Challenges and Policy Options strengthening production capacities, mineral-driven industrialisation, and increasing their exports of value-added products. Moreover, investment incentives can be used to attract investors to develop manufacturing facilities such as battery manufacturing locally. Other suggestions include establishing a robust and coherent continental green mineral strategy to fast-track development of the region’s green mineral resources to take advantage of the economic opportunities associated with the global energy transition and investing in research and development. Exam"
    ],
    "error": null,
    "gnd": [
      {
        "a.id": "active transportation",
        "b.id": "policies"
      },
      {
        "a.id": "active transportation",
        "b.id": "government"
      }
    ],
    "nlp": "Starting from active transportation, find all entities that promote it within one to five relationship steps, and return the id of active transportation and the id of each promoting entity."
  }